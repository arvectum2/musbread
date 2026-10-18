import { officialSnapshotByPath } from "./official-page-snapshots";

/**
 * Exact, source-backed fragments from the working official museum edition.
 * The user has authorized the *current* museum site as the editorial baseline.
 * These strings are checked against its archived HTML in unit tests.
 *
 * This is visit information, not a technical/legal site-wide a11y certificate
 * and does NOT invent a barrier-free route or a promise of staff availability.
 */
export const museumAccessibilitySource =
  officialSnapshotByPath("/informaciya-dlya-mgn");

export const accessVisitFacts = [
  {
    id: "entrance",
    title: "Вход и помощь",
    summary: "Перед входом со стороны улицы Михайлова, 2 установлен звонок для обращения к сотрудникам. Вход и вестибюль оборудованы пандусами.",
    sourcePhrases: [
      "Перед входом в музей с ул. Михайлова, 2 установлен звонок",
      "Вход и вестибюль оборудованы пандусами.",
    ],
  },
  {
    id: "floors",
    title: "Экспозиция и подъём",
    summary: "По сведениям музея доступны экспозиции первого и второго этажей. Для подъёма на второй этаж установлен подъёмник.",
    sourcePhrases: [
      "Доступна экспозиция первого и второго этажей.",
      "Для подъема на второй этаж установлен подъемник.",
    ],
  },
  {
    id: "toilet",
    title: "Туалет",
    summary: "Специально оборудованный туалет расположен на первом этаже.",
    sourcePhrases: ["Специально оборудованный туалет есть на первом этаже здания."],
  },
  {
    id: "vision",
    title: "Для посетителей с нарушениями зрения",
    summary: "Музей сообщает об адаптированных экскурсиях с макетами, муляжами и тактильными материалами, табличках со шрифтом Брайля, звуковых материалах и тактильной карте.",
    sourcePhrases: [
      "адаптированные экскурсии с использованием макетов, муляжей и тактильного материала",
      "табличками со шрифтом Брайля",
      "тактильная карта водных систем",
    ],
  },
  {
    id: "hearing",
    title: "Для посетителей с нарушениями слуха",
    summary: "По информации музея экспозиция частично доступна, кроме звуковых материалов. Уточните возможность экскурсии с сурдопереводчиком либо усилителями голоса.",
    sourcePhrases: [
      "экспозиция частично доступна (за исключением звуковых материалов)",
      "с привлечением услуг сурдопереводчика либо с использованием усилителей голоса",
    ],
  },
  {
    id: "guide-dog",
    title: "Собака-проводник",
    summary: "На экспозиции разрешено нахождение собаки-проводника при наличии соответствующих документов.",
    sourcePhrases: [
      "разрешено нахождение собаки-проводника (при наличии соответствующих документов)",
    ],
  },
] as const;

export const accessibilityRouteCaution = {
  text: "На маршруте от метро «Площадь Ленина» музей отмечает отсутствие тактильной и визуальной информации на пути следования.",
  sourcePhrases: [
    'От метро "Площадь Ленина"',
    "Тактильная и визуальная информация на пути следования отсутствует.",
  ],
} as const;
