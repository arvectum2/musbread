"use client";

import {useState} from "react";
import MuseumAnchor from "@/components/MuseumAnchor";
import {museumReference} from "@/data/museum-reference";
import {visitorContacts,visitorAddressMapSearchUrl} from "@/data/visitor-contacts";
import mapSource from "@/data/official-museum-map.json";

/**
 * TZ-199: actual museum-owned Yandex constructor, not guessed map pin.
 * No Yandex cookies/requests before visitor click. CMS address override
 * invalidates the pinned old location and falls back to live address search.
 */
export default function OfficialMuseumMap(){
  const [enabled,setEnabled]=useState(false);
  const verifiedAddress=visitorContacts.address===museumReference.address;
  const canEmbed=verifiedAddress
    && mapSource.constructor_id==="He-zSYLQhEw4RVkaykZ0Rpr1lOWx3f9O"
    && mapSource.map_provider==="Яндекс Карты"
    && mapSource.embedded_after_user_action_only===true;
  return <section className="official-visitor-map" aria-label="Как добраться: карта музея">
    <p><strong>Карта:</strong> исходная схема расположения музея
      {canEmbed?" из официальной страницы контактов.":" требует сверки с новым адресом из CMS."}
      {" "}<MuseumAnchor href={visitorAddressMapSearchUrl} target="_blank"
        rel="noopener noreferrer" className="text-link">
        Открыть адрес в Яндекс Картах ↗
      </MuseumAnchor></p>
    {canEmbed
      ? <>
        <p className="official-museum-program-warning">Встроенная карта Яндекса
          подключается только по вашему нажатию. После включения браузер
          обращается к Яндексу; сервис может использовать свои cookie и
          обрабатывать технические данные по собственным условиям.
          До нажатия сторонняя карта не загружается.</p>
        <button type="button" aria-controls="official-museum-yandex-map"
          aria-expanded={enabled} className="visitor-map-button"
          onClick={()=>setEnabled(previous=>!previous)}>
          {enabled?"Скрыть карту":"Показать карту музея"}
        </button>
        {enabled&&<div id="official-museum-yandex-map" className="official-map-frame">
          <iframe src={mapSource.widget_iframe_url}
            title="Карта расположения Санкт-Петербургского музея Хлеба — Яндекс Карты"
            loading="lazy" referrerPolicy="no-referrer"
            sandbox="allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox"
            allowFullScreen={false}/>
        </div>}
      </>
      : <p role="status">Музейная карта требует подтверждения после изменения адреса
          редактором. Воспользуйтесь поиском указанного адреса по ссылке выше.</p>}
  </section>;
}
