import Link from "next/link";
import type { PublicNavigationNode } from "@/data/navigation-tree";
import { guideHref } from "@/data/museum-reference";

/** Actual hierarchy: each nested <ul> is owned by its immediate parent. */
export default function NavigationBranch({nodes}: {nodes: readonly PublicNavigationNode[]}) {
  return <ul className="nav-branch">
    {nodes.map((node) => <li key={node.slug}>
      <Link prefetch={false} href={guideHref(node.slug)}>{node.title}</Link>
      {node.children.length > 0 && <NavigationBranch nodes={node.children} />}
    </li>)}
  </ul>;
}
