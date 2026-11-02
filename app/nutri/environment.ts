// App de NUTRICION (crisrodrigo.infinityfree.io). Reemplaza a src/environments/
// environment.ts solo al compilar el proyecto "nutri" (angular.json). El CI pone
// el token real desde el secreto NUTRI_TOKEN; aqui nunca va el de verdad.
export const environment = {
  apiBaseUrl: 'https://crisrodrigo.infinityfree.io/api',
  vapidPublica: '',
  apiToken: 'NUTRI_TOKEN_DEL_CI',
  // misma API publica de la demo (dashboard de la VM): solo datos simulados
  demoApi: 'https://20-150-209-104.sslip.io/demo/api'
};
