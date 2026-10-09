/**
 * Almacen durable del telefono (IndexedDB), para lo que NO se puede perder:
 * el entreno en curso y las colas de envio pendiente.
 *
 * Por que no localStorage: es sincrono, tiene ~5 MB y es lo primero que el
 * navegador borra cuando le falta espacio (en iOS, tras dias sin abrir la PWA).
 * IndexedDB, con navigator.storage.persist(), pide al navegador que NO lo
 * desaloje. Si IndexedDB no esta disponible (modo privado), se cae a
 * localStorage para no romper nada.
 */
const DB = 'gymtracker';
const STORE = 'kv';
let conexion: Promise<IDBDatabase> | null = null;
// Modo demo: todo en memoria; la base real ni se abre (ver demo.ts)
const memoriaDemo = new Map<string, unknown>();
const enDemo = () => (globalThis as unknown as { __GYM_DEMO__?: boolean }).__GYM_DEMO__ === true;

function abrir(): Promise<IDBDatabase> {
  if (!conexion) {
    conexion = new Promise((ok, falla) => {
      const req = indexedDB.open(DB, 1);
      req.onupgradeneeded = () => req.result.createObjectStore(STORE);
      req.onsuccess = () => ok(req.result);
      req.onerror = () => falla(req.error);
    });
    conexion.catch(() => (conexion = null));
  }
  return conexion;
}

function hayIdb(): boolean {
  try {
    return typeof indexedDB !== 'undefined';
  } catch {
    return false;
  }
}

async function operar<T>(modo: IDBTransactionMode, fn: (s: IDBObjectStore) => IDBRequest): Promise<T> {
  const db = await abrir();
  return new Promise<T>((ok, falla) => {
    const tx = db.transaction(STORE, modo);
    const req = fn(tx.objectStore(STORE));
    tx.oncomplete = () => ok(req.result as T);
    tx.onerror = () => falla(tx.error);
    tx.onabort = () => falla(tx.error);
  });
}

export async function leer<T>(clave: string): Promise<T | undefined> {
  if (enDemo()) return memoriaDemo.get(clave) as T | undefined;
  if (hayIdb()) {
    try {
      return await operar<T | undefined>('readonly', (s) => s.get(clave));
    } catch {
      /* cae a localStorage */
    }
  }
  try {
    const v = localStorage.getItem('idb-' + clave);
    return v ? (JSON.parse(v) as T) : undefined;
  } catch {
    return undefined;
  }
}

export async function guardar(clave: string, valor: unknown): Promise<void> {
  if (enDemo()) {
    memoriaDemo.set(clave, valor);
    return;
  }
  if (hayIdb()) {
    try {
      await operar('readwrite', (s) => s.put(valor, clave));
      return;
    } catch {
      /* cae a localStorage */
    }
  }
  try {
    localStorage.setItem('idb-' + clave, JSON.stringify(valor));
  } catch {
    /* sin espacio: no hay mas donde guardar */
  }
}

export async function borrar(clave: string): Promise<void> {
  if (enDemo()) {
    memoriaDemo.delete(clave);
    return;
  }
  if (hayIdb()) {
    try {
      await operar('readwrite', (s) => s.delete(clave));
    } catch {
      /* noop */
    }
  }
  try {
    localStorage.removeItem('idb-' + clave);
  } catch {
    /* noop */
  }
}

/** Pide almacenamiento PERSISTENTE (el navegador no lo borra por falta de
 *  espacio). Chrome lo concede a PWAs instaladas; Safari, a apps de inicio. */
export async function pedirPersistencia(): Promise<boolean> {
  if (enDemo()) return false;
  try {
    if (navigator.storage?.persisted && (await navigator.storage.persisted())) return true;
    return (await navigator.storage?.persist?.()) ?? false;
  } catch {
    return false;
  }
}
