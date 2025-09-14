// @deno-types="npm:@supabase/supabase-js@2"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import { corsHeaders } from '../_shared/cors.ts';

console.log(`Function "save-spotify-tokens" up and running!`);

Deno.serve(async (req) => {
  // Handle CORS preflight requests for browser security.
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  try {
    // 1. Create a Supabase client using environment variables.
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_ANON_KEY') ?? '',
      { global: { headers: { Authorization: req.headers.get('Authorization')! } } }
    );

    // 2. Securely get the user's data from the JWT.
    const { data: { user } } = await supabaseClient.auth.getUser();
    if (!user) throw new Error("User not found. Invalid or expired token.");

    // 3. Get the Spotify tokens from the request body.
    const { access_token, refresh_token, expires_in } = await req.json();
    if (!access_token || !refresh_token || !expires_in) {
      throw new Error("Request body must include access_token, refresh_token, and expires_in.");
    }

    const expires_at = new Date(Date.now() + expires_in * 1000).toISOString();
    
    // 4. Create a powerful "Admin" client using service role key.
    const supabaseAdmin = createClient(
        Deno.env.get('SUPABASE_URL') ?? '',
        Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    );

    // 5. Use 'upsert' to save or update the tokens in your database table.
    const { error } = await supabaseAdmin
      .from('user_tokens')
      .upsert({
        id: user.id,
        access_token: access_token,
        refresh_token: refresh_token,
        expires_at: expires_at,
      });

    if (error) throw error;

    return new Response(JSON.stringify({ message: "Tokens saved successfully" }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      status: 200,
    });

  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      status: 400,
    });
  }
});
