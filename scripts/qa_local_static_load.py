#!/usr/bin/env python3
"""TZ-317: bounded, loopback-only static HTTP baseline. NOT production load test."""
from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import http.server
import json
import math
import pathlib
import statistics
import threading
import time
import urllib.error
import urllib.request

ROUTES = ("/", "/events/", "/guide/museum/", "/search/")


def percentile(values: list[float], q: float) -> float:
    if not values:
        raise ValueError("No measurements")
    return sorted(values)[max(0, math.ceil(len(values) * q) - 1)]


def make_handler(root: pathlib.Path):
    class StaticHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(root), **kwargs)

        def log_message(self, *_args):
            pass

    return StaticHandler


def one_request(url: str) -> dict:
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=5) as result:
            data = result.read()
            return {"status": result.status, "ms": (time.perf_counter() - started) * 1000, "bytes": len(data)}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"status": 0, "ms": (time.perf_counter() - started) * 1000, "bytes": 0, "error": type(exc).__name__}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path("apps/web/out"), help="Existing local Next.js static export")
    parser.add_argument("--requests-per-route", type=int, default=60)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--output", type=pathlib.Path, default=pathlib.Path(".local_archive/tz317-local-load.json"))
    parser.add_argument("--report", type=pathlib.Path, default=pathlib.Path("docs/handoff/LOAD_TEST_REPORT_DRAFT.md"))
    args = parser.parse_args()

    if not 1 <= args.requests_per_route <= 250 or not 1 <= args.workers <= 16:
        parser.error("Limits: 1..250 requests per route; 1..16 workers. Never test external hosts.")
    root = args.root.resolve(strict=True)
    if not root.is_dir():
        parser.error("root must be a directory")
    for route in ROUTES:
        relative = route.lstrip("/")
        expected = root / relative / "index.html" if relative else root / "index.html"
        if not expected.is_file():
            parser.error(f"Required static file is missing: {expected}")

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), make_handler(root))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = f"http://127.0.0.1:{server.server_port}"
    result = {"kind": "LOCAL_LOOPBACK_ONLY_NOT_PRODUCTION", "date_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
              "served_static_root": str(root), "concurrent_clients": args.workers,
              "requests_per_route": args.requests_per_route, "routes": [],
              "external_hosts_tested": 0, "scope_note": "Static HTML only; no CDN/real assets/browser/mobile/network/API."}

    try:
        for route in ROUTES:
            # Warm up only the isolated local HTTP handler before timed measurements.
            warm = one_request(base + route)
            if warm["status"] != 200:
                raise RuntimeError(f"Unexpected warm-up status for {route}: {warm['status']}")
            started = time.perf_counter()
            with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
                samples = list(executor.map(one_request, [base + route] * args.requests_per_route))
            elapsed = time.perf_counter() - started
            latencies = [s["ms"] for s in samples if s["status"] == 200]
            failed = [s for s in samples if s["status"] != 200]
            metrics = {
                "path": route, "total": len(samples), "ok_200": len(latencies), "errors": len(failed),
                "p50_ms": round(percentile(latencies, .50), 2) if latencies else None,
                "p95_ms": round(percentile(latencies, .95), 2) if latencies else None,
                "p99_ms": round(percentile(latencies, .99), 2) if latencies else None,
                "throughput_rps": round(len(samples) / elapsed, 2),
                "mean_bytes": round(statistics.mean(s["bytes"] for s in samples if s["status"] == 200)) if latencies else 0,
            }
            result["routes"].append(metrics)
            print(f"{route:20} {metrics['ok_200']}/{metrics['total']} HTTP 200, p95={metrics['p95_ms']} ms, {metrics['throughput_rps']} req/s")
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    rows = "\n".join(
        f"| `{item['path']}` | {item['ok_200']}/{item['total']} | {item['errors']} | {item['p50_ms']} | {item['p95_ms']} | {item['p99_ms']} | {item['throughput_rps']} |"
        for item in result["routes"]
    )
    report = f"""# TZ-317 · Отдельный отчёт о ЛОКАЛЬНОМ нагрузочном baseline статической сборки

**Дата (UTC):** {result['date_utc']}
**Статус:** предварительный технический тест, не нагрузочные испытания промышленного контура музея и не акт приёмки.
**Цель:** зафиксировать воспроизводимые значения для HTML с безопасной многопоточной отдачей на собственном Mac mini, без обращения к музею или внешним серверам.

## Метод
- Источник: уже собранная статика Next.js `apps/web/out` (локальный путь проверенной сборки).
- Тестовый сервер Python ThreadingHTTPServer работает **строго на 127.0.0.1**, порт случайный.
- {args.workers} одновременных клиентов; {args.requests_per_route} измеренных GET на каждую из {len(ROUTES)} HTML-страниц (плюс один прогрев).
- Обработчик читает весь ответ, измеряется HTTP-запрос с точки зрения клиента: p50 / p95 / p99 latency, успешные HTTP 200, ошибки и throughput.
- Ограничение интенсивности зафиксировано в скрипте: максимум 250 запросов на маршрут и 16 потоков. **Удалённые хосты недопустимы.**

## Измерения
| Страница | HTTP 200 | Ошибки | p50, мс | p95, мс | p99, мс | Запросов/с |
|---|---:|---:|---:|---:|---:|---:|
{rows}

Машинный исходник чисел: приватный локальный JSON в `{args.output}` (не публиковать системную информацию и данные устройства).

## Что этим НЕ проверялось
Реальная посещаемость музея, CDN, защита DDoS, база данных и закрытый Laravel, пропускная способность каналов, билеты/оплаты, долговременная устойчивость, TLS/Nginx, изображение/JS, требования времени отрисовки на устройствах. Для TZ-317 **обязателен ещё отдельный итоговый отчёт нагрузочного тестирования на разрешённом стенде/production после согласования сценариев с музеем**.

## Следующие шаги для закрытия TZ-317
1. Заказчик предоставляет одобренный тестовый контур, нагрузочный профиль и письменное разрешение.
2. Определяются потоки статических страниц, кеширования, публикации и интеграций без реальных платежей, тесты отказа/восстановления и критерии приёмки.
3. Отдельно выполняется браузерный аудит скорости и комплексное функциональное тестирование (см. `docs/QA_PREAWARD_REPORT.md` и `docs/TZ241_250_PERFORMANCE_LAYOUT.md`).
4. Фиксируются входные параметры, параметры железа/сети, графики, ошибки, выводы и акт согласования музеем. Пока статус **Частично**.
"""
    report_path = args.report.resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    print("Local JSON:", output)
    print("Draft report:", report_path)
    return 1 if any(row["errors"] for row in result["routes"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
