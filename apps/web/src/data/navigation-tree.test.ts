import test from "node:test";
import assert from "node:assert/strict";
import { buildPublicNavigationTree, findPublicNavigationNode } from "./navigation-tree.ts";
import type { PublishedSection } from "./types";
const section=(slug:string,parent_slug:string|null,sort_order:number,title=slug):PublishedSection=>({slug,parent_slug,sort_order,title,legacy_path:null});

test("TZ-072: true three-level published navigation groups retain the direct parent",()=>{
 const tree=buildPublicNavigationTree([
  section("grandchild","child",12),section("other","root",2),
  section("child","root",1),section("root",null,5),section("another",null,2),
 ]);
 assert.deepEqual(tree.map(n=>n.slug),["another","root"]);
 assert.deepEqual(tree[1].children.map(n=>n.slug),["child","other"]);
 assert.deepEqual(tree[1].children[0].children.map(n=>n.slug),["grandchild"]);
 assert.deepEqual(tree[1].children[1].children,[]);
 assert.equal(findPublicNavigationNode(tree,"grandchild")?.parentSlug,"child");
 assert.equal(findPublicNavigationNode(tree,"absent"),undefined);
});
test("TZ-076: new service and subgroup appear from CMS data, no manually coded routes",()=>{
 const snapshot=[section("visitors",null,0),section("services","visitors",0),section("new-kiosk","services",0)];
 const tree=buildPublicNavigationTree(snapshot);
 assert.deepEqual(tree[0].children[0].children.map(n=>n.slug),["new-kiosk"]);
 assert.deepEqual(buildPublicNavigationTree(snapshot.slice(0,2))[0].children[0].children,[]);
});
test("Fail closed: duplicate slugs, missing parents, cycles, malformed URLs",()=>{
 assert.throws(()=>buildPublicNavigationTree([section("x",null,0),section("x",null,0)]));
 assert.throws(()=>buildPublicNavigationTree([section("child","unknown",0)]));
 assert.throws(()=>buildPublicNavigationTree([section("x","y",0),section("y","x",0)]));
 assert.throws(()=>buildPublicNavigationTree([section("x/../../private",null,0)]));
 assert.deepEqual(buildPublicNavigationTree([]),[]);
});
