import Link from "next/link";
import { museumReference, REFERENCE_DATE } from "@/data/museum-reference";
import { content, sections } from "@/data/content";

const englishPages = content.entries.filter((entry) => entry.translations?.en).map((entry) => {
  const section = Object.entries(sections).find(([, item]) => item.type === entry.type)?.[0];
  return { title: entry.translations!.en.title, url: "/en/" + section + "/" + entry.slug + "/" };
});
export default function EnglishFooter() {
  return <footer className="site-footer" lang="en">
    <div className="footer-info">
      <strong>Museum of Bread — information preview</strong>
      <p>Address (official text in Russian): {museumReference.address}</p>
      <p><a href={museumReference.phoneHref}>{museumReference.phone}</a></p>
      <p><a href={museumReference.emailHref}>{museumReference.email}</a></p>
      <p className="footer-source">Reference contact details from the existing museum website,
        checked {REFERENCE_DATE}. Confirmation by the museum is pending.</p>
    </div>
    <div className="footer-navigation">
      <h2>English pages</h2>
      {englishPages.length === 0
        ? <p>English translations are being prepared.</p>
        : englishPages.map((entry) => <Link key={entry.url} href={entry.url}>{entry.title}</Link>)}
    </div>
    <div className="footer-legal">
      <h2>Links</h2>
      <Link href="/" lang="ru">Russian-language museum website preview</Link>
      <a href={museumReference.privacyPolicyUrl} target="_blank" rel="noopener noreferrer">
        Privacy notice on the official Russian-language site ↗</a>
      <p className="footer-source">Prototype only. No visitor details are collected here.</p>
    </div>
  </footer>;
}
