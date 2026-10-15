"use client";
import { useEffect, useSyncExternalStore } from "react";

const KEY = "musbread-vision-mode";
const CHANGE = "musbread-vision-change";
function subscribe(callback: () => void) {
  window.addEventListener("storage", callback);
  window.addEventListener(CHANGE, callback);
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener(CHANGE, callback);
  };
}
function getSnapshot() {
  try { return window.localStorage.getItem(KEY) === "enabled"; }
  catch { return false; }
}
function getServerSnapshot() { return false; }

export default function VisionMode() {
  const on = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  useEffect(() => {
    document.documentElement.dataset.visionMode = on ? "on" : "off";
  }, [on]);
  function toggle() {
    const next = !on;
    try { window.localStorage.setItem(KEY, next ? "enabled" : "disabled"); }
    catch { document.documentElement.dataset.visionMode = next ? "on" : "off"; }
    window.dispatchEvent(new Event(CHANGE));
  }
  return <button className="vision-toggle" type="button" aria-pressed={on} onClick={toggle}>
    {on ? "Обычная версия" : "Для слабовидящих"}
  </button>;
}
