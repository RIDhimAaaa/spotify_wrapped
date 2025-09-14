import { useState, useEffect } from 'react';
import { supabase } from '../supabaseClient.js'; // Make sure this path is correct

// This is the helper function that calls our Edge Function
async function sendSpotifyTokensToBackend(session) {
  if (!session?.provider_token || !session?.provider_refresh_token) {
    console.log("Provider tokens not found in this session event.");
    return;
  }

  console.log("SIGNED_IN event detected. Sending Spotify tokens to Edge Function...");

  try {
    const { error } = await supabase.functions.invoke('save-spotify-tokens', {
      body: {
        access_token: session.provider_token,
        refresh_token: session.provider_refresh_token,
        expires_in: session.expires_in,
      }
    });

    if (error) {
      throw error;
    }

    console.log("Successfully stored Spotify tokens via Edge Function.");

  } catch (error) {
    console.error("Error sending Spotify tokens to Edge Function:", error.message);
  }
}

// The main useAuth hook
export const useAuth = () => {
  const [session, setSession] = useState(null);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // onAuthStateChange is designed to handle the initial session as well.
    // It fires an 'INITIAL_SESSION' event on page load if a user is logged in.
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        setSession(session);
        setUser(session?.user ?? null);
        setLoading(false);

        // This is the crucial part: only send tokens on the initial sign-in event
        if (event === 'SIGNED_IN') {
          await sendSpotifyTokensToBackend(session);
        }
      }
    );

    // Unsubscribe from the listener when the component unmounts
    return () => subscription.unsubscribe();
  }, []);

  return { session, user, loading };
};