import Link from "@/components/MuseumLink";
import MuseumAnchor from "@/components/MuseumAnchor";
import {entriesInCmsSection, entryPublicHref} from "@/data/content";
import {visitorContacts} from "@/data/visitor-contacts";

/**
 * TZ-145 specifically prohibits a shop purchase function.
 * Entries are editorial display-only information (type=page), not stock,
 * prices, inventory, orders, payments, checkout, customer accounts or forms.
 */
export default function MuseumShopShowcase(){
  const items = entriesInCmsSection("museum-shop")
    .filter(entry=>entry.type==="page" && entry.slug!=="museum-shop");
  return <section aria-label="Витрина музейного магазина без продажи" className="museum-shop-showcase">
    <h2>Музейный магазин</h2>
    <p>Информационная витрина сувенирной продукции. <strong>На сайте ничего не продаётся:</strong> здесь
      нет корзины, оформления заказа или онлайн-оплаты.</p>
    {items.length>0
      ? <div className="museum-shop-grid">{items.map(item=>
        <article className="museum-shop-item" key={item.slug}>
          <h3>{item.title}</h3>
          {item.excerpt && <p>{item.excerpt}</p>}
          <Link className="text-link" href={entryPublicHref(item)}>Посмотреть описание →</Link>
        </article>)}</div>
      : <div className="museum-shop-empty" role="status">
          <h3>Каталог сувениров уточняется</h3>
          <p>На действующем сайте музея не обнаружен подтверждённый каталог товаров
            для переноса. Раздел предусмотрен ТЗ и может наполняться редактором
            после получения настоящих названий, описаний и разрешённых изображений.</p>
        </div>}
    <div className="museum-shop-contact">
      <h3>Уточнить ассортимент и условия приобретения в музее</h3>
      <p>Телефон: <MuseumAnchor href={visitorContacts.phoneHref}>{visitorContacts.phone}</MuseumAnchor>.
        Адрес и часы работы указаны на странице <Link href="/guide/plan-visit/">«Спланировать визит»</Link>.</p>
      <p>Раздел носит справочный характер: заявки, платежи и персональные данные посетителей
        через витрину не собираются.</p>
    </div>
  </section>;
}
