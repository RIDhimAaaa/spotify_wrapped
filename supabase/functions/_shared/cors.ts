// This file centralizes the CORS headers for all your functions.
// It allows your frontend (running on localhost) to securely call your Edge Function.
export const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};