import type { PageServerLoad } from './$types';
import { error } from '@sveltejs/kit';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const load: PageServerLoad = async ({ params, fetch }) => {
  const res = await fetch(`${API_URL}/api/v1/businesses/${params.slug}`);

  if (!res.ok) {
    throw error(404, 'Business not found');
  }

  const business = await res.json();
  return { business };
};
