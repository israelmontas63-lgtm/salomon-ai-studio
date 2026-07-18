/**
 * core/peripherals/VoiceCore — puerto de audio + noise gate (300–3400 Hz).
 * Sensibilidad 80% + compresión adaptativa (supresión de ruido).
 */
(function (global) {
  "use strict";

  var HP_HZ = 300;
  var LP_HZ = 3400;
  var SENSITIVITY = 0.8; // 80%
  var state = {
    noiseGate: false,
    ctx: null,
    stream: null,
    nodes: null,
    ready: false,
  };

  function disconnectNodes() {
    try {
      if (state.nodes) {
        Object.keys(state.nodes).forEach(function (k) {
          try {
            state.nodes[k].disconnect();
          } catch (e) {}
        });
      }
      if (state.stream) {
        state.stream.getTracks().forEach(function (t) {
          t.stop();
        });
      }
    } catch (e) {}
    state.nodes = null;
    state.stream = null;
    if (state.ctx) {
      try {
        state.ctx.close();
      } catch (e) {}
    }
    state.ctx = null;
    state.ready = false;
  }

  function buildChain(stream) {
    var AC = global.AudioContext || global.webkitAudioContext;
    if (!AC) return null;
    var ctx = new AC();
    var src = ctx.createMediaStreamSource(stream);

    // Filtro de voz humana: descarta <300Hz y >3400Hz
    var hp = ctx.createBiquadFilter();
    hp.type = "highpass";
    hp.frequency.value = HP_HZ;
    hp.Q.value = 0.707;

    var lp = ctx.createBiquadFilter();
    lp.type = "lowpass";
    lp.frequency.value = LP_HZ;
    lp.Q.value = 0.707;

    // Sensibilidad 80%
    var gain = ctx.createGain();
    gain.gain.value = SENSITIVITY;

    // Compresor = supresión de ruido adaptativa ligera
    var comp = ctx.createDynamicsCompressor();
    comp.threshold.value = -32;
    comp.knee.value = 18;
    comp.ratio.value = 6;
    comp.attack.value = 0.003;
    comp.release.value = 0.18;

    // Analyser (no conectamos a speakers — solo procesamos)
    var analyser = ctx.createAnalyser();
    analyser.fftSize = 256;

    src.connect(hp);
    hp.connect(lp);
    lp.connect(gain);
    gain.connect(comp);
    comp.connect(analyser);

    return { ctx: ctx, src: src, hp: hp, lp: lp, gain: gain, comp: comp, analyser: analyser };
  }

  async function openMic() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      console.warn("[VoiceCore] getUserMedia no disponible");
      return false;
    }
    try {
      // noiseSuppression / echoCancellation en el driver
      var stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          channelCount: 1,
        },
        video: false,
      });
      disconnectNodes();
      var chain = buildChain(stream);
      if (!chain) {
        stream.getTracks().forEach(function (t) {
          t.stop();
        });
        return false;
      }
      state.ctx = chain.ctx;
      state.stream = stream;
      state.nodes = chain;
      state.ready = true;
      global.__SalomonVoicePort = global.__SalomonVoicePort || {};
      global.__SalomonVoicePort.noiseGate = true;
      global.__SalomonVoicePort.bandHz = [HP_HZ, LP_HZ];
      global.__SalomonVoicePort.sensitivity = SENSITIVITY;
      global.__SalomonVoicePort.sincronizado = true;
      return true;
    } catch (e) {
      console.warn("[VoiceCore] mic open fail", e && e.message);
      return false;
    }
  }

  var VoiceCore = {
    enableNoiseGate: function (on) {
      state.noiseGate = on !== false;
      if (!state.noiseGate) {
        disconnectNodes();
        console.info("[VoiceCore] noiseGate OFF");
        return Promise.resolve(false);
      }
      return openMic().then(function (ok) {
        console.info(
          "[VoiceCore] noiseGate",
          ok ? "ON" : "FAIL",
          "band=" + HP_HZ + "-" + LP_HZ + "Hz sens=" + SENSITIVITY
        );
        return ok;
      });
    },
    isReady: function () {
      return !!state.ready;
    },
    getBand: function () {
      return { minHz: HP_HZ, maxHz: LP_HZ, sensitivity: SENSITIVITY };
    },
    /** Mantener puerto listo sin bloquear STT del navegador */
    warm: function () {
      return VoiceCore.enableNoiseGate(true).then(function (ok) {
        // Liberar device para SpeechRecognition, conservar parámetros
        if (ok) disconnectNodes();
        state.ready = true;
        return ok;
      });
    },
  };

  global.SalomonCore = global.SalomonCore || {};
  global.SalomonCore.VoiceCore = VoiceCore;
})(typeof window !== "undefined" ? window : globalThis);
