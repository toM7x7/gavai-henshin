const THREE_VERSION = "0.180.0";
const THREE_VRM_VERSION = "3.4.4";

let gltfLoaderClassPromise = null;
let threeVrmModulePromise = null;

export const VRM_RUNTIME_TARGETS = Object.freeze({
  threeVersion: THREE_VERSION,
  threeVrmVersion: THREE_VRM_VERSION,
});

async function importFirstSuccessful(loaders) {
  let lastError = null;
  for (const load of loaders) {
    try {
      return await load();
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError || new Error("Module import failed.");
}

async function getGLTFLoaderClass() {
  if (!gltfLoaderClassPromise) {
    gltfLoaderClassPromise = importFirstSuccessful([
      () => import("three/addons/loaders/GLTFLoader.js"),
      () =>
        import(`https://cdn.jsdelivr.net/npm/three@${THREE_VERSION}/examples/jsm/loaders/GLTFLoader.js`),
      () =>
        import(`https://unpkg.com/three@${THREE_VERSION}/examples/jsm/loaders/GLTFLoader.js?module`),
    ]).then((mod) => {
      if (!mod?.GLTFLoader) throw new Error("GLTFLoader is not available.");
      return mod.GLTFLoader;
    });
  }
  return gltfLoaderClassPromise;
}

async function getThreeVrmModule() {
  if (!threeVrmModulePromise) {
    threeVrmModulePromise = importFirstSuccessful([
      () => import("@pixiv/three-vrm"),
      () =>
        import(
          `https://cdn.jsdelivr.net/npm/@pixiv/three-vrm@${THREE_VRM_VERSION}/lib/three-vrm.module.min.js`
        ),
      () =>
        import(
          `https://unpkg.com/@pixiv/three-vrm@${THREE_VRM_VERSION}/lib/three-vrm.module.min.js?module`
        ),
    ]);
  }
  return threeVrmModulePromise;
}

export async function loadVrmScene(path, { onProgress } = {}) {
  const normalizedPath = String(path || "").trim();
  if (!normalizedPath) {
    throw new Error("VRM path is empty.");
  }

  const GLTFLoader = await getGLTFLoaderClass();
  let threeVrm = null;
  try {
    threeVrm = await getThreeVrmModule();
  } catch {
    threeVrm = null;
  }

  const loader = new GLTFLoader();
  if (threeVrm?.VRMLoaderPlugin) {
    loader.register((parser) => new threeVrm.VRMLoaderPlugin(parser));
  }

  const gltf = await new Promise((resolve, reject) => {
    loader.load(
      normalizedPath,
      resolve,
      (progress) => {
        if (typeof onProgress !== "function") return;
        if (!progress?.total) {
          onProgress({ loaded: progress?.loaded || 0, total: progress?.total || 0, ratio: null });
          return;
        }
        const ratio = Math.max(0, Math.min(1, progress.loaded / progress.total));
        onProgress({ loaded: progress.loaded, total: progress.total, ratio });
      },
      reject
    );
  });

  const vrmInstance = gltf.userData?.vrm || null;
  if (vrmInstance && threeVrm?.VRMUtils?.rotateVRM0) {
    try {
      // Recommended by three-vrm docs for VRM 0.0 orientation compatibility.
      threeVrm.VRMUtils.rotateVRM0(vrmInstance);
    } catch {
      // Non-fatal.
    }
  }

  const model = vrmInstance?.scene || gltf.scene || gltf.scenes?.[0] || null;
  return {
    gltf,
    model,
    vrmInstance,
    source: vrmInstance ? "three-vrm" : "gltf-fallback",
  };
}
