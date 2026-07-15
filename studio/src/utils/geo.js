let cached = null;

export function getCachedGeo() {
  return cached;
}

export function initGeo() {
  return new Promise((resolve) => {
    if (!navigator.geolocation) {
      resolve(null);
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        cached = {
          lat: pos.coords.latitude,
          lon: pos.coords.longitude,
        };
        resolve(cached);
      },
      () => resolve(null),
      { timeout: 4000, maximumAge: 600000 }
    );
  });
}
