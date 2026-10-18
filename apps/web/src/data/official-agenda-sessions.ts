import source from "./official-agenda-sessions.json";

export type OfficialMuseumSession={
  slug:string;
  date:string;
  time:string;
  title:string;
  age_min:number;
  category:string;
  original_row:string;
  source_urls:string[];
  source_html_sha256:string[];
};
/** Real, explicitly dated individual museum programme instances. */
export const officialMuseumSessions=source.sessions as OfficialMuseumSession[];
export const officialSessionSourceStats={
  bulletins:source.original_bulletin_count,
  raw:source.raw_rows,
  unique:source.unique_sessions,
  snapshot:source.created_utc,
};
export type SourceAgendaSection="agenda-excursions"|"agenda-children"|"agenda-meetings"|"agenda-workshops"|"agenda-festivals"|"agenda-exhibitions"|"agenda-archive"|"all";
export function sourceAgendaMatches(s:OfficialMuseumSession,section:SourceAgendaSection):boolean{
  switch(section){
    case "all":case "agenda-archive":return true;
    case "agenda-excursions":return s.category==="Экскурсия";
    case "agenda-workshops":return s.category==="Мастер-класс";
    case "agenda-meetings":return s.category==="Литературная гостиная";
    case "agenda-children":return s.age_min<=10; // Explicit age marker, not claim of child exclusivity
    case "agenda-festivals":case "agenda-exhibitions":return false;
  }
}
