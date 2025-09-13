import React, { useState, useEffect } from 'react';
import { createClient } from '@supabase/supabase-js';

// --- Supabase Client Initialization ---
// This section replaces the need for a separate supabaseClient.js file.
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

// A check to ensure environment variables are loaded
if (!supabaseUrl || !supabaseAnonKey) {
  console.error("Supabase URL or Anon Key is missing. Make sure to set them in your .env file.");
}
const supabase = createClient(supabaseUrl, supabaseAnonKey);


// --- Style Injector Component ---
// This component injects all necessary CSS into the document head,
// replacing the need for a separate App.css file.
const StyleInjector = () => {
  useEffect(() => {
    const style = document.createElement('style');
    style.textContent = `
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

      body {
        margin: 0;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
          'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
          sans-serif;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
        background-color: #121212;
        color: #ffffff;
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 100vh;
      }

      .container {
        text-align: center;
      }

      .login-card, .dashboard {
        background-color: #282828;
        padding: 40px;
        border-radius: 12px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
        max-width: 400px;
        width: 100%;
        margin: 20px;
      }

      h1 {
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 16px;
      }

      p {
        color: #b3b3b3;
        font-size: 1rem;
        line-height: 1.5;
        margin-bottom: 32px;
      }

      .button {
        background-color: #1DB954;
        color: #ffffff;
        border: none;
        padding: 14px 28px;
        border-radius: 500px;
        font-size: 1rem;
        font-weight: 600;
        cursor: pointer;
        transition: background-color 0.2s ease-in-out, transform 0.1s ease-in-out;
        text-transform: uppercase;
        letter-spacing: 1px;
      }

      .button:hover {
        background-color: #1ED760;
      }

      .button:active {
        transform: scale(0.98);
      }
    `;
    document.head.appendChild(style);

    return () => {
      document.head.removeChild(style);
    };
  }, []);

  return null;
};


// --- Main App Component ---
function App() {
  const [session, setSession] = useState(null);

  useEffect(() => {
    // Check for an active session when the component mounts
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
    });

    // Listen for changes in authentication state (login/logout)
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        setSession(session);
      }
    );

    // Cleanup subscription on component unmount
    return () => subscription.unsubscribe();
  }, []);

  // Function to handle Spotify OAuth login
  async function handleLogin() {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'spotify',
      options: {
        // This is where we define the permissions we need
        scopes: 'user-top-read user-read-email',
      },
    });

    if (error) {
      console.error('Error during login:', error.message);
    }
  }

  // Function to handle logout
  async function handleLogout() {
    const { error } = await supabase.auth.signOut();
    if (error) {
      console.error('Error during logout:', error.message);
    }
  }

  return (
    <>
      <StyleInjector />
      <div className="container">
        {session ? (
          // Show this if the user is logged in
          <div className="dashboard">
            <h1>Welcome!</h1>
            <p>You are now logged in.</p>
            <p><strong>Email:</strong> {session.user.email}</p>
            <button className="button" onClick={handleLogout}>
              Logout
            </button>
          </div>
        ) : (
          // Show this if the user is not logged in
          <div className="login-card">
            <h1>Spotify Stats Project</h1>
            <p>Get your on-demand listening stats.</p>
            <button className="button" onClick={handleLogin}>
              Login with Spotify
            </button>
          </div>
        )}
      </div>
    </>
  );
}

export default App;