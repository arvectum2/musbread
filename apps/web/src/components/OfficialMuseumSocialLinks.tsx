import MuseumAnchor from "@/components/MuseumAnchor";
import {museumReference} from "@/data/museum-reference";

/** Social networks listed by the actual museum on /kontakty.
 * Direct links are explicit user navigation: no third-party trackers/embeds. */
export default function OfficialMuseumSocialLinks(){
  return <section className="official-museum-socials" aria-label="Официальные сообщества музея">
    <h3>Сообщества музея</h3>
    <p>Аккаунты опубликованы в <MuseumAnchor href="https://muzei-xleb.ru/kontakty"
      target="_blank" rel="noopener noreferrer">официальных контактах музея ↗</MuseumAnchor>.
      Внешние сервисы открываются только по ссылке, без загрузки
      социальной ленты на этом сайте.</p>
    <div className="official-museum-social-buttons">
      <MuseumAnchor className="text-link" href={museumReference.vkUrl}
        target="_blank" rel="noopener noreferrer">
        ВКонтакте — сообщество музея ↗
      </MuseumAnchor>
      <MuseumAnchor className="text-link" href={museumReference.maxUrl}
        target="_blank" rel="noopener noreferrer">
        MAX — канал музея ↗
      </MuseumAnchor>
    </div>
  </section>;
}
