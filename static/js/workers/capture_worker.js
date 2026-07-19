/**
 * Salomón AI — Worker de captura (encode fuera del main thread)
 */
self.onmessage = async function (ev) {
  var data = ev.data || {};
  if (data.type !== "ENCODE_FRAME" || !data.bitmap) return;

  try {
    var w = data.width || data.bitmap.width;
    var h = data.height || data.bitmap.height;
    var canvas = new OffscreenCanvas(w, h);
    var ctx = canvas.getContext("2d", { alpha: false });
    if (data.mirror) {
      ctx.translate(w, 0);
      ctx.scale(-1, 1);
    }
    ctx.drawImage(data.bitmap, 0, 0, w, h);
    try {
      data.bitmap.close();
    } catch (_) {}

    var blob = await canvas.convertToBlob({ type: "image/jpeg", quality: 0.85 });
    var dataUrl = await new Promise(function (resolve, reject) {
      var reader = new FileReader();
      reader.onload = function () {
        resolve(reader.result);
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });

    self.postMessage({ type: "ENCODE_DONE", dataUrl: dataUrl });
  } catch (err) {
    self.postMessage({
      type: "ENCODE_FAIL",
      error: String(err && err.message ? err.message : err),
    });
  }
};
