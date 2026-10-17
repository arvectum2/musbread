import Image from "next/image";
import { museumIdentity } from "@/data/museum-identity";

/** Single accessible identity for header/footer; no fabricated official logo. */
export default function MuseumIdentity({ locale = "ru" }: { locale?: "ru" | "en" }) {
  const { name, approvedLogoSrc } = museumIdentity[locale];
  return <span className="museum-identity">
    {approvedLogoSrc && <Image
      src={approvedLogoSrc} width={64} height={64} alt="" aria-hidden="true"
      className="museum-identity-logo" unoptimized />}
    <span className="museum-identity-name">{name}</span>
  </span>;
}
