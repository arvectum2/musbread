import Link from "@/components/MuseumLink";

/** Shortcuts only to routes already exported in BOTH the reference and the
 * CMS-driven tree. These are navigational choices, never invented facts,
 * social-proof popularity claims or unauthorized museum content. */
export const visitorTasks = [
  {href:"/guide/plan-visit/",label:"Как добраться",context:"Адрес и планирование посещения"},
  {href:"/guide/tickets-and-benefits/",label:"Билеты и льготы",context:"Официальные условия и билетная площадка"},
  {href:"/events/",label:"Афиша",context:"События и архив"},
  {href:"/excursions/",label:"Экскурсии",context:"Опубликованные программы и описания"},
  {href:"/guide/accessible-museum/",label:"Доступная среда",context:"Условия посещения"},
  {href:"/guide/museum-contacts/",label:"Контакты",context:"Часы работы, телефон и почта"},
  {href:"/guide/museum-documents/",label:"Документы музея",context:"Официальные сведения и документы"},
] as const;

export default function VisitorTaskLinks({compact=false}:{compact?:boolean}){
  return <nav className={compact?"visitor-tasks visitor-tasks-compact":"visitor-tasks"}
    aria-label="Быстрые переходы по задачам посетителя" id="visitor-tasks">
    <h2>Быстрые переходы</h2>
    <p className="visitor-tasks-note">Выберите задачу — без поиска по всему меню. Сведения, перенесённые с действующего сайта, требуют подтверждения перед запуском.</p>
    <div className="visitor-task-grid">{visitorTasks.map(task=>
      <Link href={task.href} className="visitor-task-link" key={task.href}>
        <strong>{task.label}<span aria-hidden="true"> ↗</span></strong>
        <span>{task.context}</span>
      </Link>
    )}</div>
  </nav>;
}
