import Link from "next/link";
import type { PublicNavigationNode } from "@/data/navigation-tree";

/** Actual hierarchy: each nested <ul> is owned by its immediate parent. */
export default function NavigationBranch({nodes}: {nodes: readonly PublicNavigationNode[]}) {
  return <ul className="nav-branch">
    {nodes.map((node) => <li key={node.slug}>
      <Link prefetch={false} href={`/guide/${node.slug}/`}>{node.title}</Link>
      {node.children.length > 0 && <NavigationBranch nodes={node.children} />}
    </li>)}
  </ul>;
}
