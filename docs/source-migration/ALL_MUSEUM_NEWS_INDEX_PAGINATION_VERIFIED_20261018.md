# Верификация всей существующей пагинации новостей Музея хлеба

**18.10.2026, Mac mini.** Фактические исходные HTML-страницы музейного архива `/novosty?page=1` — `/novosty?page=27` загружены и сохранены на ArvectumSSD, каждая имеет по **10 уникальных реальных ссылок**. На последнем индексе `?page=27` нет ссылки «следующая»; последняя новость датирована 01.09.2019. Основной индекс `/novosty` содержит ещё 10 последних публикаций. Проверено **270 архивных + 10 последних = 280 уникальных индексных URL**.

Эта проверка **доказывает полноту именно видимой пагинации новостей**, но не утверждает, что на старом сайте вообще нет иных скрытых/неиндексируемых URL. [CSV всех исходных архивных адресов](ALL_HISTORICAL_MUSEUM_NEWS_URLS_20261018.csv).

| Исходный индекс | Новейший материал | Старейший материал | Ссылок | SHA-256 исходного HTML |
|---|---|---|---:|---|
| [1](https://muzei-xleb.ru/novosty?page=1) | 2026-08-31 | 2026-06-28 | 10 | `a186d74f2eff49e846c8231d624073578658e2dae57e49b17b7c18e7ab0e3405` |
| [2](https://muzei-xleb.ru/novosty?page=2) | 2026-06-22 | 2026-05-13 | 10 | `c05d6e86022d1b68a8a079c37b74fa2181bac1944d75778daf116034e1dd0ce9` |
| [3](https://muzei-xleb.ru/novosty?page=3) | 2026-05-12 | 2026-04-07 | 10 | `d91df0ff056199a8a18452abdc10919fe9283c080ed035c4d5c8cbba42be7bcc` |
| [4](https://muzei-xleb.ru/novosty?page=4) | 2026-03-31 | 2026-03-05 | 10 | `7c7b810797b3b3a947fca4040a94948aec92ebdbdaceb514c5aacca0cc62c1f6` |
| [5](https://muzei-xleb.ru/novosty?page=5) | 2026-03-02 | 2026-01-23 | 10 | `d7c2ba7c05c48d8c08ab8aec9481f69bdc4f85bcca2576a43e42540d09cd846f` |
| [6](https://muzei-xleb.ru/novosty?page=6) | 2026-01-21 | 2025-12-10 | 10 | `5868991a5ff2a0e3e68562c0e4a0d13774670463144507c4cdcf8239ac637eb6` |
| [7](https://muzei-xleb.ru/novosty?page=7) | 2025-12-09 | 2025-10-24 | 10 | `da668dc8b81117c877d79ec7815b30e18405da486e472f0bc744cd77ddc7c618` |
| [8](https://muzei-xleb.ru/novosty?page=8) | 2025-09-22 | 2024-12-27 | 10 | `a803216e150beb27b5b4908c9e90ab884e2e6ccca6d1c54445d741e0b680a6e1` |
| [9](https://muzei-xleb.ru/novosty?page=9) | 2024-12-26 | 2024-10-02 | 10 | `06faeb7d969ed4a3bf2b3508c2f0affa63e6c372eee50eba684e9e5847e80b8c` |
| [10](https://muzei-xleb.ru/novosty?page=10) | 2024-10-02 | 2024-05-15 | 10 | `2cd2174074b06525e7ab6d703a3ce878b688b9de1c9822bdf526f4c846eae62f` |
| [11](https://muzei-xleb.ru/novosty?page=11) | 2024-05-06 | 2024-01-26 | 10 | `2316cbe3cfcc2d6ea6728efa78d797df633a26191df4b9317f17f1f35407246a` |
| [12](https://muzei-xleb.ru/novosty?page=12) | 2024-01-11 | 2023-10-27 | 10 | `b72029d1427b724f81a7c2d7ad89bfd9eb4baee4ec6d98ee2951c805417f6c64` |
| [13](https://muzei-xleb.ru/novosty?page=13) | 2023-10-26 | 2023-07-07 | 10 | `bd087b408b140c2b63bc195043500387334833ddb685e0e5993a6e79129c86e9` |
| [14](https://muzei-xleb.ru/novosty?page=14) | 2023-06-19 | 2023-03-24 | 10 | `92077247950e902339e5c606f690e9d5fb9961fe991506fdbfd452e21a519cb3` |
| [15](https://muzei-xleb.ru/novosty?page=15) | 2023-03-02 | 2022-12-21 | 10 | `62c4922dc17f4da09ebf455d6ee1716b814bb40d08cbff191df80e81ad2c6378` |
| [16](https://muzei-xleb.ru/novosty?page=16) | 2022-11-28 | 2022-10-12 | 10 | `831dd043e3806d83e0529982619d64bfbdaf9bf958ad931b841ea8d8f19f64fd` |
| [17](https://muzei-xleb.ru/novosty?page=17) | 2022-10-04 | 2022-06-08 | 10 | `51aded85f6c03be57aebfa356c8287b0ecceb9801302e2aa9c50bebe10b68dc2` |
| [18](https://muzei-xleb.ru/novosty?page=18) | 2022-05-27 | 2022-03-25 | 10 | `76058504d1c6fbd8d99fd4c3f4795c95d21894cddf73f59d497566a5c53a6f78` |
| [19](https://muzei-xleb.ru/novosty?page=19) | 2022-03-22 | 2021-12-28 | 10 | `c968029cff431edc78d8cbf6b96404bad0d79a4156733e49aa74ec1f875ac074` |
| [20](https://muzei-xleb.ru/novosty?page=20) | 2021-12-16 | 2021-09-02 | 10 | `29f26b9344e3ac10f473a528f7b3b7e57da7b8d3a2b4118f1b65506f30594fd1` |
| [21](https://muzei-xleb.ru/novosty?page=21) | 2021-08-26 | 2021-06-07 | 10 | `2e8964af7877f689f7ce8906ef942f31db4b1e120d3b9aaa15eab66bd108078f` |
| [22](https://muzei-xleb.ru/novosty?page=22) | 2021-05-28 | 2021-04-09 | 10 | `884ffb01db0b5808f3171b4043338aa666d6e6777e82308bd4b9a674f416eeba` |
| [23](https://muzei-xleb.ru/novosty?page=23) | 2021-04-09 | 2021-01-26 | 10 | `6a01783c9e47556451933bd74f4bfc3448aa8f7a30d030a4de941f566423f5e8` |
| [24](https://muzei-xleb.ru/novosty?page=24) | 2021-01-15 | 2020-10-23 | 10 | `213e4b951a4163c5816eb527dc0eab3d6f27a29fd159facde637305fc8fd897f` |
| [25](https://muzei-xleb.ru/novosty?page=25) | 2020-10-21 | 2020-07-07 | 10 | `ce490ccee8235e50f850824ff3fab9bb6f1b56789e616a317102f21e87becd19` |
| [26](https://muzei-xleb.ru/novosty?page=26) | 2020-06-03 | 2020-01-14 | 10 | `25d96947772db33bd7213031b50901e1185ea6320f3d69fda52381f964e9c0cc` |
| [27](https://muzei-xleb.ru/novosty?page=27) | 2019-12-27 | 2019-09-01 | 10 | `5a26a8cd74dabee616ab2c58cf3a0ec1a0ffc9ed7a816cdb1f27a239fb9cb4e1` |

## Реальные годы публикаций

| Год | Исторических новостей |
|---|---:|
| 2026 | 51 |
| 2025 | 28 |
| 2024 | 32 |
| 2023 | 34 |
| 2022 | 44 |
| 2021 | 42 |
| 2020 | 29 |
| 2019 | 10 |

Контроль: `.local_archive/official-site-originals/news-list-page-N-20261018.html`, `scripts/capture_official_museum_news_archive.py` и `tests/test_official_museum_news_archive.py`; каждый сохранённый HTML и его десять конкретных ссылок проверены, дублей URL нет. Для публикации полной версии необходимо, помимо списка, проверить **HTML каждой отдельной статьи, изображение-плакат и её старый маршрут**.
