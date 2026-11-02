/** Emoji por alimento: la "foto" de cada porcion en el diseno de Nutri (sin fotos
 *  de internet: nada de derechos ni de peso extra en la pagina). */
export const EMOJI: Record<string, string> = {
  huevo: '🥚', frijol: '🫘', lentejas: '🥣', soya: '🌱', atun: '🐟', sardina: '🐟', pollo: '🍗', res: '🥩',
  pescado: '🐠', leche: '🥛', yogur_griego: '🥣', queso: '🧀', tortilla: '🫓', avena: '🌾', cacahuate: '🥜',
  scoop: '💪', otro: '➕',
  f_pastor: '🌮', f_asada: '🌮', f_canasta: '🌮', f_quesadilla: '🫓', f_torta: '🥪', f_corrida: '🍛',
  f_pozole: '🍲', f_enchiladas: '🌯', f_chilaquiles: '🍳', f_tamal: '🫔', f_rostizado: '🍗',
  f_hamburguesa: '🍔', f_pizza: '🍕', f_sushi: '🍣', f_burrito: '🌯', f_gorditas: '🫓', f_caldo: '🍜',
  f_coctel: '🍤', f_esquite: '🌽', f_licuado: '🥤'
};

export const emojiDe = (id: string): string => EMOJI[id] ?? '🍽️';

/** La comida que toca segun la hora (para el boton + del centro). */
export function tiempoPorHora(d = new Date()): string {
  const h = d.getHours();
  return h < 11 ? 'desayuno' : h < 16 ? 'comida' : h < 19 ? 'colacion' : 'cena';
}
