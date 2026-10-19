import React, { useState, useEffect } from 'react';
import './styles.css';
import { getCities, getShows } from './api';

// Poster fallbacks for realistic movie look
const SAMPLE_POSTERS = [
  "https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=500&q=80",
  "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=500&q=80",
  "https://images.unsplash.com/photo-1517604931442-7e0c8ed2963c?w=500&q=80",
  "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=500&q=80"
];

export default function App() {
  const [cities, setCities] = useState(['Mumbai', 'Dehradun', 'Delhi', 'Bangalore']);
  const [selectedCity, setSelectedCity] = useState('Dehradun');
  const [shows, setShows] = useState([]);
  const [search, setSearch] = useState('');

  useEffect(() => {
    getCities().then(res => { if(res && res.length) setCities(res); }).catch(() => {});
    getShows(selectedCity).then(res => { if(res) setShows(res); }).catch(() => {});
  }, [selectedCity]);

  return (
    <div className="bms-app">
      {/* Top Navbar */}
      <header className="bms-navbar">
        <div className="bms-nav-top">
          <div className="bms-logo">TICKET<span>RUSH</span></div>
          <div>
            <select 
              className="bms-location-btn" 
              value={selectedCity} 
              onChange={(e) => setSelectedCity(e.target.value)}
            >
              {cities.map(c => <option key={c} value={c}>{c} ›</option>)}
            </select>
            <button className="bms-login-btn" style={{ marginLeft: '10px' }}>Log in</button>
          </div>
        </div>
        <input 
          type="text" 
          className="bms-search-bar" 
          placeholder="Search for Movies, Events, Plays & Sports..." 
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </header>

      {/* Category Icon Strip */}
      <div className="bms-categories">
        <div className="bms-cat-item"><div className="bms-cat-icon">🎬</div><span className="bms-cat-title">Movies</span></div>
        <div className="bms-cat-item"><div className="bms-cat-icon">🎵</div><span className="bms-cat-title">Music</span></div>
        <div className="bms-cat-item"><div className="bms-cat-icon">🎭</div><span className="bms-cat-title">Comedy</span></div>
        <div className="bms-cat-item"><div className="bms-cat-icon">⚽</div><span className="bms-cat-title">Sports</span></div>
        <div className="bms-cat-item"><div className="bms-cat-icon">🎟️</div><span className="bms-cat-title">Workshops</span></div>
      </div>

      {/* Promo Banner */}
      <div className="bms-banner">
        <div>
          <h3>STREAM INSIDIOUS</h3>
          <p>Step into the dark world, right from your home!</p>
        </div>
        <button className="bms-login-btn">Explore</button>
      </div>

      {/* Recommended Movies Section */}
      <main className="bms-section">
        <div className="bms-section-header">
          <h2 className="bms-section-title">Recommended Movies in {selectedCity}</h2>
          <a href="#all" className="bms-see-all">See All ›</a>
        </div>

        <div className="bms-movies-grid">
          {shows.length > 0 ? (
            shows.map((show, idx) => (
              <div className="bms-card" key={show.id || idx}>
                <div className="bms-poster-wrapper">
                  <img 
                    src={show.poster_url || SAMPLE_POSTERS[idx % SAMPLE_POSTERS.length]} 
                    alt={show.title} 
                    className="bms-poster-img"
                  />
                  <div className="bms-rating-tag">
                    <span><span className="bms-star">★</span> {show.rating || '8.5'}</span>
                    <span>{show.votes || '2.4K'} votes</span>
                  </div>
                </div>
                <div className="bms-card-details">
                  <div className="bms-movie-title">{show.title || show.name}</div>
                  <div className="bms-movie-sub">{show.genre || 'Action/Drama'}</div>
                </div>
              </div>
            ))
          ) : (
            /* Fallback Mock UI Cards matching screenshot */
            [
              { title: "Nayyi Navelli", rating: "7.3", votes: "3.8K", genre: "Drama/Romance", img: "https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=500&q=80" },
              { title: "Prahaar", rating: "9.2", votes: "4.9K", genre: "Action/Thriller", img: "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=500&q=80" },
              { title: "Drishyam 3", rating: "8.8", votes: "12K", genre: "Mystery/Crime", img: "https://images.unsplash.com/photo-1517604931442-7e0c8ed2963c?w=500&q=80" }
            ].map((m, i) => (
              <div className="bms-card" key={i}>
                <div className="bms-poster-wrapper">
                  <img src={m.img} alt={m.title} className="bms-poster-img" />
                  <div className="bms-rating-tag">
                    <span><span className="bms-star">★</span> {m.rating}</span>
                    <span>{m.votes}</span>
                  </div>
                </div>
                <div className="bms-card-details">
                  <div className="bms-movie-title">{m.title}</div>
                  <div className="bms-movie-sub">{m.genre}</div>
                </div>
              </div>
            ))
          )}
        </div>
      </main>

      {/* Bottom Navigation */}
      <nav className="bms-bottom-nav">
        <a href="#home" className="bms-bottom-item active"><span className="bms-bottom-icon">🏠</span>Home</a>
        <a href="#movies" className="bms-bottom-item"><span className="bms-bottom-icon">🎬</span>Movies</a>
        <a href="#events" className="bms-bottom-item"><span className="bms-bottom-icon">🎟️</span>Live Events</a>
        <a href="#profile" className="bms-bottom-item"><span className="bms-bottom-icon">👤</span>Profile</a>
      </nav>
    </div>
  );
}