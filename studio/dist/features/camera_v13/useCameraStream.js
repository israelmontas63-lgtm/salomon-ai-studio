/**
 * Compat shim — el pipeline vive en MediaStreamManager (v20).
 * Mantiene export useCameraStream por si hay imports legacy.
 */
export { MediaStreamManager, ENGINE_STATUS } from "./MediaStreamManager.js";

export function useCameraStream() {
  throw new Error(
    "[CameraEngine] useCameraStream v16 eliminado — usa MediaStreamManager (v20)"
  );
}
