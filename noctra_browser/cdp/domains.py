from __future__ import annotations


class BrowserDomain:
    GET_VERSION = "Browser.getVersion"
    CLOSE = "Browser.close"


class TargetDomain:
    ATTACH_TO_TARGET = "Target.attachToTarget"
    ATTACHED_TO_TARGET = "Target.attachedToTarget"
    CLOSE_TARGET = "Target.closeTarget"
    CREATE_TARGET = "Target.createTarget"
    GET_TARGETS = "Target.getTargets"
    SET_AUTO_ATTACH = "Target.setAutoAttach"
    SET_DISCOVER_TARGETS = "Target.setDiscoverTargets"


class PageDomain:
    ADD_SCRIPT_TO_EVALUATE_ON_NEW_DOCUMENT = "Page.addScriptToEvaluateOnNewDocument"
    CAPTURE_SCREENSHOT = "Page.captureScreenshot"
    CREATE_ISOLATED_WORLD = "Page.createIsolatedWorld"
    ENABLE = "Page.enable"
    GET_FRAME_TREE = "Page.getFrameTree"
    GET_LAYOUT_METRICS = "Page.getLayoutMetrics"
    NAVIGATE = "Page.navigate"
    RELOAD = "Page.reload"
    REMOVE_SCRIPT_TO_EVALUATE_ON_NEW_DOCUMENT = "Page.removeScriptToEvaluateOnNewDocument"


class RuntimeDomain:
    ADD_BINDING = "Runtime.addBinding"
    CALL_FUNCTION_ON = "Runtime.callFunctionOn"
    DISABLE = "Runtime.disable"
    ENABLE = "Runtime.enable"
    EVALUATE = "Runtime.evaluate"
    RELEASE_OBJECT = "Runtime.releaseObject"
    RUN_IF_WAITING_FOR_DEBUGGER = "Runtime.runIfWaitingForDebugger"


class DomDomain:
    DESCRIBE_NODE = "DOM.describeNode"
    GET_BOX_MODEL = "DOM.getBoxModel"
    GET_DOCUMENT = "DOM.getDocument"
    QUERY_SELECTOR = "DOM.querySelector"
    QUERY_SELECTOR_ALL = "DOM.querySelectorAll"
    RESOLVE_NODE = "DOM.resolveNode"


class InputDomain:
    DISPATCH_KEY_EVENT = "Input.dispatchKeyEvent"
    DISPATCH_MOUSE_EVENT = "Input.dispatchMouseEvent"
    INSERT_TEXT = "Input.insertText"


class NetworkDomain:
    ENABLE = "Network.enable"
    GET_COOKIES = "Network.getCookies"
    SET_COOKIES = "Network.setCookies"
    SET_EXTRA_HTTP_HEADERS = "Network.setExtraHTTPHeaders"
    SET_USER_AGENT_OVERRIDE = "Network.setUserAgentOverride"


class EmulationDomain:
    SET_DEVICE_METRICS_OVERRIDE = "Emulation.setDeviceMetricsOverride"
    SET_TIMEZONE_OVERRIDE = "Emulation.setTimezoneOverride"
    SET_USER_AGENT_OVERRIDE = "Emulation.setUserAgentOverride"


class LogDomain:
    ENABLE = "Log.enable"
