<?php

declare(strict_types=1);

namespace App\Support;

use MoonShine\Laravel\Models\MoonshineUser;

/** Verify that a previously downloaded ADMIN review pack still describes this CMS. */
final class MuseumReviewPackVerifier
{
    private const MAX_BYTES = 5 * 1024 * 1024;

    /** @return array{ok:bool,code:string,message:string,candidate_sha256?:string,baseline_release?:string} */
    public function verify(string $path): array
    {
        // The pack is a local operator-supplied review file, not an HTTP URL.
        // Fail closed on missing files, symlinks, directories and large inputs.
        if ($path === '' || str_contains($path, '://') || is_link($path)
            || ! is_file($path) || ! is_readable($path) || filesize($path) > self::MAX_BYTES) {
            return $this->fail('invalid_file', 'Локальный файл отчёта недоступен или слишком велик.');
        }
        try {
            $raw = file_get_contents($path);
            if ($raw === false) return $this->fail('invalid_file', 'Не удалось прочитать отчёт.');
            $json = json_decode($raw, true, 32, JSON_THROW_ON_ERROR);
            if (! is_array($json) || ! is_array($json['document'] ?? null)
                || ! is_string($json['sha256'] ?? null)
                || preg_match('/^[a-f0-9]{64}$/D', $json['sha256']) !== 1) {
                return $this->fail('invalid_format', 'Отчёт не соответствует ожидаемому формату.');
            }
            $document = $json['document'];
            $calculated = hash('sha256', json_encode($document, MuseumReleaseReviewPack::JSON_FLAGS));
            if (! hash_equals($calculated, $json['sha256'])) {
                return $this->fail('checksum_mismatch', 'Отчёт изменён или повреждён.');
            }
            if (($document['kind'] ?? '') !== 'musbread_editorial_review_only'
                || ($document['scope'] ?? '') !== 'all'
                || ($document['schema_version'] ?? null) !== 1) {
                return $this->fail('not_admin_report', 'Для проверки выпуска нужен полный отчёт администратора.');
            }
            // Never guess authority from a supplied JSON. Recompute with an
            // actual superuser to avoid accepting a section-limited packet.
            $admin = MoonshineUser::query()->get()->first(static fn (MoonshineUser $user) => $user->isSuperUser());
            if ($admin === null) return $this->fail('no_admin', 'Не найден администратор для полной проверки.');

            $current = app(MuseumReleaseReviewPack::class)->prepare($admin);
            if ($current === null) {
                return $this->fail('missing_baseline', 'Подтверждённый локальный исходный релиз недоступен.');
            }
            if (! hash_equals($current['sha256'], $json['sha256'])
                || $current['document'] !== $document) {
                return $this->fail('stale_review', 'CMS или локальный релиз изменились с момента подготовки отчёта.');
            }
            if ($current['document']['preflight']['critical_errors'] !== 0) {
                return $this->fail('critical_issues', 'В подготовленной версии есть критические ошибки.');
            }
            return [
                'ok' => true, 'code' => 'current',
                'message' => 'Состав данных соответствует проверенному отчёту; согласование музеем не подтверждается.',
                'candidate_sha256' => $current['document']['candidate']['snapshot_sha256'],
                'baseline_release' => $current['document']['baseline']['local_release_id'],
            ];
        } catch (\Throwable $exception) {
            // Report the error server-side without sending paths/SQL/private data to CLI consumers.
            report($exception);
            return $this->fail('verification_failed', 'Проверка не завершилась. Данные не публиковались.');
        }
    }

    /** @return array{ok:bool,code:string,message:string} */
    private function fail(string $code, string $message): array
    {
        return ['ok' => false, 'code' => $code, 'message' => $message];
    }
}
