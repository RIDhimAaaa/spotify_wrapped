import { useState, useEffect } from 'react';
import { supabase } from '../supabaseClient.js'; // Corrected import path

export const useAuth = () => {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 1. Get the initial session. Supabase client automatically handles token refresh.
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setLoading(false);
    });

    // 2. Listen for authentication state changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        // 3. This is the crucial part: Check for the SIGNED_IN event
        if (event === 'SIGNED_IN' && session?.provider_token) {
          // 4. If it's a new sign-in with Spotify, immediately send the tokens to our secure backend
          await sendSpotifyTokensToBackend(session);
        }
        
        // Update the session state for the UI
        setSession(session);
        setLoading(false);
      }
    );

    // Cleanup subscription on component unmount
    return () => subscription.unsubscribe();
  }, []);

  return { session, loading };
};

// Helper function to call our backend API
async function sendSpotifyTokensToBackend(session) {
  try {
    const response = await fetch('/api/tokens/spotify', {
      method: 'POST',
      headers: {
        // The Supabase JWT is the "App Key" for our own backend
        'Authorization': `Bearer ${session.access_token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        // The Spotify tokens are the "Spotify Key"
        access_token: session.provider_token,
        refresh_token: session.provider_refresh_token,
        expires_in: session.expires_in,
      })
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to store Spotify tokens');
    }

    console.log("Spotify tokens securely stored on the backend.");
    // For enhanced security, you could consider clearing them from localStorage now,
    // but the Supabase client library manages its own session storage effectively.

  } catch (error) {
    console.error("Error sending Spotify tokens to backend:", error);
  }
}