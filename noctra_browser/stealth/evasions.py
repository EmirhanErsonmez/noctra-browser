from __future__ import annotations

from noctra_browser.stealth.config import StealthConfig
from noctra_browser.utils.json import json_dumps

# Prelude installs a self-erasing toolkit shared by every evasion. The key idea
# is that all spoofing flows through helpers that keep Function.prototype.toString
# returning "[native code]" and keep Object.getOwnPropertyDescriptor faithful,
# without ever using a Proxy (proxies are themselves detectable through the
# prototype-chain ownKeys trap that leaks via the inspector). The toolkit is
# stored on a non-enumerable Symbol and deleted from the global once evasions run.
PRELUDE = r"""
(() => {
  if (window['__noctra']) return;
  const toStr = Function.prototype.toString;
  const nativeMap = new WeakMap();
  const nativeName = (fn) => {
    try { return fn.name || ''; } catch (e) { return ''; }
  };
  const patchedToString = function toString() {
    if (nativeMap.has(this)) {
      return 'function ' + nativeMap.get(this) + '() { [native code] }';
    }
    return toStr.call(this);
  };
  nativeMap.set(patchedToString, 'toString');
  Object.defineProperty(Function.prototype, 'toString', {
    value: patchedToString,
    configurable: true,
    writable: true,
    enumerable: false,
  });

  const markNative = (fn, name) => {
    nativeMap.set(fn, name || nativeName(fn));
    return fn;
  };

  // Replace a data/getter property with a getter that looks native.
  const patchGetter = (target, prop, value, name) => {
    const getter = markNative(function () { return value; }, name || ('get ' + prop));
    Object.defineProperty(target, prop, {
      get: getter,
      configurable: true,
      enumerable: target.propertyIsEnumerable ? target.propertyIsEnumerable(prop) : false,
    });
  };

  // Replace a method, keeping its toString native and preserving descriptor shape.
  const patchMethod = (target, prop, impl, name) => {
    markNative(impl, name || prop);
    const descriptor = Object.getOwnPropertyDescriptor(target, prop);
    Object.defineProperty(target, prop, {
      value: impl,
      configurable: descriptor ? descriptor.configurable : true,
      writable: descriptor ? descriptor.writable : true,
      enumerable: descriptor ? descriptor.enumerable : false,
    });
  };

  const api = { markNative, patchGetter, patchMethod, toStr };
  Object.defineProperty(window, '__noctra', {
    value: api,
    configurable: true,
    enumerable: false,
    writable: false,
  });
})();
"""

WEBDRIVER = r"""
(() => {
  const N = window['__noctra']; if (!N) return;
  if (typeof Navigator === 'undefined') return;
  // webdriver lives on Navigator.prototype with a native getter in a real browser.
  const proto = Navigator.prototype;
  delete proto.webdriver;
  N.patchGetter(proto, 'webdriver', undefined, 'get webdriver');
})();
"""

NAVIGATOR_PLUGINS = r"""
(() => {
  const N = window['__noctra']; if (!N) return;
  if (typeof Navigator === 'undefined' || typeof PluginArray === 'undefined') return;
  const pdf = { type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format' };
  const chromePdf = { type: 'application/x-google-chrome-pdf', suffixes: 'pdf', description: 'Portable Document Format' };
  const defs = [
    { name: 'PDF Viewer', filename: 'internal-pdf-viewer', mimes: [pdf, chromePdf] },
    { name: 'Chrome PDF Viewer', filename: 'internal-pdf-viewer', mimes: [pdf, chromePdf] },
    { name: 'Chromium PDF Viewer', filename: 'internal-pdf-viewer', mimes: [pdf, chromePdf] },
    { name: 'Microsoft Edge PDF Viewer', filename: 'internal-pdf-viewer', mimes: [pdf, chromePdf] },
    { name: 'WebKit built-in PDF', filename: 'internal-pdf-viewer', mimes: [pdf, chromePdf] },
  ];

  const mimeArray = Object.create(MimeTypeArray.prototype);
  const plugins = defs.map((def) => {
    const plugin = Object.create(Plugin.prototype);
    Object.defineProperties(plugin, {
      name: { value: def.name, enumerable: true },
      filename: { value: def.filename, enumerable: true },
      description: { value: 'Portable Document Format', enumerable: true },
      length: { value: def.mimes.length, enumerable: true },
    });
    def.mimes.forEach((m, i) => {
      const mime = Object.create(MimeType.prototype);
      Object.defineProperties(mime, {
        type: { value: m.type, enumerable: true },
        suffixes: { value: m.suffixes, enumerable: true },
        description: { value: m.description, enumerable: true },
        enabledPlugin: { value: plugin, enumerable: true },
      });
      Object.defineProperty(plugin, i, { value: mime, enumerable: false });
      Object.defineProperty(plugin, m.type, { value: mime, enumerable: false });
      if (!mimeArray[m.type]) {
        const idx = Object.keys(mimeArray).length;
        Object.defineProperty(mimeArray, m.type, { value: mime, enumerable: false });
        Object.defineProperty(mimeArray, idx, { value: mime, enumerable: true });
      }
    });
    N.patchMethod(plugin, 'item', (i) => plugin[i] ?? null, 'item');
    N.patchMethod(plugin, 'namedItem', (n) => plugin[n] ?? null, 'namedItem');
    return plugin;
  });

  const pluginArray = Object.create(PluginArray.prototype);
  plugins.forEach((plugin, i) => {
    Object.defineProperty(pluginArray, i, { value: plugin, enumerable: true });
    Object.defineProperty(pluginArray, plugin.name, { value: plugin, enumerable: false });
  });
  Object.defineProperty(pluginArray, 'length', { value: plugins.length });
  N.patchMethod(pluginArray, 'item', (i) => pluginArray[i] ?? null, 'item');
  N.patchMethod(pluginArray, 'namedItem', (n) => pluginArray[n] ?? null, 'namedItem');
  N.patchMethod(pluginArray, 'refresh', () => undefined, 'refresh');

  Object.defineProperty(mimeArray, 'length', { value: Object.keys(mimeArray).length });
  N.patchMethod(mimeArray, 'item', (i) => mimeArray[i] ?? null, 'item');
  N.patchMethod(mimeArray, 'namedItem', (n) => mimeArray[n] ?? null, 'namedItem');

  N.patchGetter(Navigator.prototype, 'plugins', pluginArray, 'get plugins');
  N.patchGetter(Navigator.prototype, 'mimeTypes', mimeArray, 'get mimeTypes');
})();
"""

WINDOW_CHROME = r"""
(() => {
  const N = window['__noctra']; if (!N) return;
  if (typeof window === 'undefined' || typeof document === 'undefined') return;
  if (window.chrome && window.chrome.runtime) return;
  const now = () => Date.now() / 1000;
  const chrome = {
    app: {
      isInstalled: false,
      InstallState: { DISABLED: 'disabled', INSTALLED: 'installed', NOT_INSTALLED: 'not_installed' },
      RunningState: { CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run', RUNNING: 'running' },
    },
    runtime: {
      OnInstalledReason: { CHROME_UPDATE: 'chrome_update', INSTALL: 'install', SHARED_MODULE_UPDATE: 'shared_module_update', UPDATE: 'update' },
      OnRestartRequiredReason: { APP_UPDATE: 'app_update', OS_UPDATE: 'os_update', PERIODIC: 'periodic' },
      PlatformArch: { ARM: 'arm', ARM64: 'arm64', MIPS: 'mips', MIPS64: 'mips64', X86_32: 'x86-32', X86_64: 'x86-64' },
      PlatformOs: { ANDROID: 'android', CROS: 'cros', LINUX: 'linux', MAC: 'mac', OPENBSD: 'openbsd', WIN: 'win' },
      RequestUpdateCheckStatus: { NO_UPDATE: 'no_update', THROTTLED: 'throttled', UPDATE_AVAILABLE: 'update_available' },
    },
  };
  N.patchMethod(chrome.runtime, 'connect', () => {}, 'connect');
  N.patchMethod(chrome.runtime, 'sendMessage', () => {}, 'sendMessage');
  N.patchMethod(chrome, 'csi', () => ({ startE: now(), onloadT: now(), pageT: now(), tran: 15 }), 'csi');
  N.patchMethod(chrome, 'loadTimes', () => ({
    commitLoadTime: now(), connectionInfo: 'h2', finishDocumentLoadTime: now(),
    finishLoadTime: now(), firstPaintAfterLoadTime: 0, firstPaintTime: now(),
    navigationType: 'Other', npnNegotiatedProtocol: 'h2', requestTime: now(),
    startLoadTime: now(), wasAlternateProtocolAvailable: false, wasFetchedViaSpdy: true,
    wasNpnNegotiated: true,
  }), 'loadTimes');
  const install = () => {
    const target = window.chrome;
    if (!target) {
      Object.defineProperty(window, 'chrome', {
        value: chrome, configurable: true, writable: true, enumerable: false,
      });
      return;
    }
    // Chrome already installed loadTimes/csi/app; only add what is missing,
    // using defineProperty because the object is frozen against assignment.
    for (const key of ['runtime', 'app', 'csi', 'loadTimes']) {
      if (!(key in target)) {
        try {
          Object.defineProperty(target, key, {
            value: chrome[key], configurable: true, writable: true, enumerable: true,
          });
        } catch (e) {}
      }
    }
  };
  // window.chrome may be installed by the browser slightly after this script.
  if (window.chrome && window.chrome.loadTimes) {
    install();
  } else {
    install();
    document.addEventListener('DOMContentLoaded', install, { once: true });
  }
})();
"""

PERMISSIONS = r"""
(() => {
  const N = window['__noctra']; if (!N) return;
  const proto = Permissions.prototype;
  const original = proto.query;
  N.patchMethod(proto, 'query', function query(parameters) {
    if (parameters && parameters.name === 'notifications') {
      return Promise.resolve(Object.setPrototypeOf({
        state: Notification.permission, onchange: null, name: 'notifications',
      }, PermissionStatus.prototype));
    }
    return original.call(this, parameters);
  }, 'query');
})();
"""

WEBGL_TEMPLATE = r"""
(() => {
  const N = window['__noctra']; if (!N) return;
  const vendor = %(vendor)s;
  const renderer = %(renderer)s;
  const patch = (proto) => {
    if (!proto) return;
    const origGetParameter = proto.getParameter;
    N.patchMethod(proto, 'getParameter', function getParameter(p) {
      if (p === 37445) return vendor;
      if (p === 37446) return renderer;
      return origGetParameter.call(this, p);
    }, 'getParameter');
  };
  if (typeof WebGLRenderingContext !== 'undefined') patch(WebGLRenderingContext.prototype);
  if (typeof WebGL2RenderingContext !== 'undefined') patch(WebGL2RenderingContext.prototype);
})();
"""

# Deterministic per-session canvas/audio noise: a fixed seed produces stable
# fingerprints across reads within a session (real devices are stable) while
# differing from the raw headless output. Avoids the "unstable fingerprint" tell.
CANVAS_NOISE = r"""
(() => {
  const N = window['__noctra']; if (!N) return;
  // Deterministic noise keyed by pixel position, so repeated reads of the same
  // canvas yield identical output (stable, like a real device) while still
  // differing from the raw headless fingerprint.
  const tweak = (data) => {
    for (let i = 0; i < data.length; i += 4) {
      const p = (i * 1103515245 + 12345) & 0x7fffffff;
      if ((p & 31) === 0) {
        data[i] = data[i] ^ ((p >> 5) & 1);
        data[i + 1] = data[i + 1] ^ ((p >> 6) & 1);
        data[i + 2] = data[i + 2] ^ ((p >> 7) & 1);
      }
    }
  };
  if (typeof CanvasRenderingContext2D === 'undefined' || typeof HTMLCanvasElement === 'undefined') return;
  const proto = CanvasRenderingContext2D.prototype;
  const origGetImageData = proto.getImageData;
  N.patchMethod(proto, 'getImageData', function getImageData(x, y, w, h) {
    const result = origGetImageData.call(this, x, y, w, h);
    tweak(result.data);
    return result;
  }, 'getImageData');
  const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
  N.patchMethod(HTMLCanvasElement.prototype, 'toDataURL', function toDataURL() {
    try {
      const w = this.width, h = this.height;
      const src = this.getContext('2d');
      if (src && w && h) {
        const copy = document.createElement('canvas');
        copy.width = w; copy.height = h;
        const cctx = copy.getContext('2d');
        const data = origGetImageData.call(src, 0, 0, w, h);
        tweak(data.data);
        cctx.putImageData(data, 0, 0);
        return origToDataURL.apply(copy, arguments);
      }
    } catch (e) {}
    return origToDataURL.apply(this, arguments);
  }, 'toDataURL');
})();
"""

AUDIO_NOISE = r"""
(() => {
  const N = window['__noctra']; if (!N) return;
  if (typeof AnalyserNode === 'undefined') return;
  const proto = AnalyserNode.prototype;
  if (!proto) return;
  const origGetFloatFrequencyData = proto.getFloatFrequencyData;
  N.patchMethod(proto, 'getFloatFrequencyData', function getFloatFrequencyData(array) {
    origGetFloatFrequencyData.call(this, array);
    for (let i = 0; i < array.length; i++) {
      array[i] = array[i] + (Math.sin(i) * 1e-4);
    }
  }, 'getFloatFrequencyData');
})();
"""

HAIRLINE_AND_MISC = r"""
(() => {
  const N = window['__noctra']; if (!N) return;
  if (typeof Navigator !== 'undefined') {
    try { N.patchGetter(Navigator.prototype, 'maxTouchPoints', 0, 'get maxTouchPoints'); } catch (e) {}
  }
  if (typeof window !== 'undefined' && window.outerWidth === 0 && window.outerHeight === 0) {
    N.patchGetter(window, 'outerWidth', window.innerWidth, 'get outerWidth');
    N.patchGetter(window, 'outerHeight', window.innerHeight + 85, 'get outerHeight');
  }
})();
"""


def _navigator_property_script(config: StealthConfig) -> str:
    # NAV resolves to Navigator.prototype in a window and WorkerNavigator.prototype
    # in a worker, so the same spoof keeps main thread and workers consistent.
    parts: list[str] = []
    if config.navigator_languages:
        languages = json_dumps(list(config.languages))
        parts.append(
            f"N.patchGetter(NAV, 'languages', Object.freeze({languages}), 'get languages');"
        )
    if config.navigator_vendor:
        vendor = json_dumps(config.vendor)
        platform = json_dumps(config.platform)
        parts.append(f"N.patchGetter(NAV, 'vendor', {vendor}, 'get vendor');")
        parts.append(f"N.patchGetter(NAV, 'platform', {platform}, 'get platform');")
    if config.navigator_hardware:
        parts.append(
            f"N.patchGetter(NAV, 'hardwareConcurrency', "
            f"{config.hardware_concurrency}, 'get hardwareConcurrency');"
        )
        parts.append(
            f"N.patchGetter(NAV, 'deviceMemory', {config.device_memory}, 'get deviceMemory');"
        )
    if not parts:
        return ""
    body = "\n  ".join(parts)
    return (
        "(() => {\n"
        "  const N = window['__noctra']; if (!N) return;\n"
        "  const NAV = Object.getPrototypeOf(navigator);\n"
        f"  {body}\n"
        "})();"
    )


def build_evasion_scripts(config: StealthConfig) -> list[str]:
    if not config.enabled:
        return []
    scripts: list[str] = [PRELUDE]
    if config.webdriver:
        scripts.append(WEBDRIVER)
    if config.navigator_plugins:
        scripts.append(NAVIGATOR_PLUGINS)
    navigator_props = _navigator_property_script(config)
    if navigator_props:
        scripts.append(navigator_props)
    if config.window_chrome:
        scripts.append(WINDOW_CHROME)
    if config.permissions:
        scripts.append(PERMISSIONS)
    if config.webgl_vendor:
        scripts.append(
            WEBGL_TEMPLATE
            % {
                "vendor": json_dumps(config.webgl_vendor_string),
                "renderer": json_dumps(config.webgl_renderer_string),
            }
        )
    if config.canvas_noise:
        scripts.append(CANVAS_NOISE)
    if config.audio_noise:
        scripts.append(AUDIO_NOISE)
    scripts.append(HAIRLINE_AND_MISC)
    scripts.extend(config.extra_evasions)
    return scripts
