import { useEffect, useState } from "react";

/** Día/noche según hora local (hook usado por App). */
export function useDayNight() {
  const [isDay, setIsDay] = useState(() => {
    const h = new Date().getHours();
    return h >= 6 && h < 19;
  });

  useEffect(() => {
    const id = window.setInterval(() => {
      const h = new Date().getHours();
      setIsDay(h >= 6 && h < 19);
    }, 60_000);
    return () => window.clearInterval(id);
  }, []);

  return isDay;
}

export function useTypewriter() {
  return { text: "", done: true };
}
