import Link from "@/components/MuseumLink";
import MuseumAnchor from "@/components/MuseumAnchor";
import RichText from "@/components/RichText";
import OfficialMuseumSourcePhotos from "@/components/OfficialMuseumSourcePhotos";
import type {OfficialMuseumNewsItem} from "@/data/official-museum-news";

/** Static detail URL for each ORIGINAL museum news article, not just a feed anchor. */
export default function OfficialMuseumNewsDetail({article,originalPath=false}:{article:OfficialMuseumNewsItem;originalPath?:boolean}){
  return <article className="section inner-page museum-detail" data-official-original-news={article.slug}>
    <nav aria-label="Хлебные крошки" className="breadcrumbs">
      <Link href="/">Главная</Link><span aria-hidden="true">/</span>
      <Link href="/news/">Новости</Link><span aria-hidden="true">/</span>
      <span aria-current="page">{article.title}</span>
    </nav>
    <span className="eyebrow">ОРИГИНАЛЬНАЯ ПУБЛИКАЦИЯ МУЗЕЯ · АРХИВ</span>
    <h1>{article.title}</h1>
    <p>Дата музейного сообщения: <time dateTime={article.published_on}>
      {article.published_on.split("-").reverse().join(".")}</time>. Это не дата
      действующего мероприятия или подтверждённой записи.</p>
    <OfficialMuseumSourcePhotos photos={article.image_links} label={article.title} limit={12}/>
    {article.image_only
      ? <p>Музей опубликовал это объявление изображением без текста. Ниже показан
          сохранённый подлинный плакат; расшифровка или добавленные сведения отсутствуют.</p>
      : <RichText html={article.html}/>}
    {originalPath
      ? <p>Первоначальный адрес музейной публикации сохранён для совместимости с историческими ссылками и поисковыми системами.</p>
      : <p>Источник: <MuseumAnchor href={article.source_url} className="text-link"
          rel="noopener noreferrer">оригинальный адрес музейной новости</MuseumAnchor>.
          Эта техническая копия указывает canonical на первоначальный адрес.</p>}
    <Link href="/news/" className="text-link">← К новостям и архиву музея</Link>
  </article>;
}
