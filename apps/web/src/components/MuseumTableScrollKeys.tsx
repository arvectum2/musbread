"use client";

import {useEffect,useRef} from "react";

/** Firefox/Chromium permit native keyboard scrolling of overflowed tables;
 * macOS WebKit may focus the table but ignore ArrowLeft/ArrowRight. This
 * narrow enhancer handles ONLY horizontal scrolling of the focused source
 * table. It does not alter Tab/Shift+Tab, typing or screenreader navigation
 * to other controls and never manipulates the document scroll container.
 */
export default function MuseumTableScrollKeys(){
  const marker=useRef<HTMLSpanElement>(null);
  useEffect(()=>{
    const container=marker.current?.parentElement;
    if(!container)return;
    const tables=[...container.querySelectorAll<HTMLTableElement>('table[tabindex="0"]')];
    const cleanup=tables.map(table=>{
      function scrollTable(e:KeyboardEvent){
        if(e.target!==table
          ||(e.key!=="ArrowRight"&&e.key!=="ArrowLeft")
          ||e.altKey||e.ctrlKey||e.metaKey||e.shiftKey
          ||table.scrollWidth<=table.clientWidth+2)return;
        const direction=e.key==="ArrowRight"?1:-1;
        const next=Math.max(0,Math.min(table.scrollWidth-table.clientWidth,
          table.scrollLeft+direction*96));
        if(next===table.scrollLeft)return;
        e.preventDefault();
        table.scrollLeft=next;
      }
      table.addEventListener("keydown",scrollTable);
      return ()=>table.removeEventListener("keydown",scrollTable);
    });
    return ()=>cleanup.forEach(fn=>fn());
  },[]);
  return <span ref={marker} hidden aria-hidden="true"/>;
}
