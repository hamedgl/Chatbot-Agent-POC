import React from 'react';
import { 
  User, Mail, Phone, Calendar, Sparkles, 
  Moon, Sun, Globe, Bell, BellOff, Clock, 
  Award, MapPin 
} from 'lucide-react';

export default function Dashboard({ 
  profile, hobbies, events, settings, loading 
}) {
  
  // Custom avatar initials generator
  const getInitials = (name) => {
    if (!name) return 'A';
    return name.split(' ').map(n => n[0]).join('').toUpperCase();
  };

  return (
    <div className="dashboard-container">
      {/* 1. Profile Panel */}
      <div>
        <div className="section-header">
          <User size={20} />
          <h2>User Profile</h2>
        </div>
        
        {profile ? (
          <div className="profile-panel">
            <div className="profile-header">
              <div className="profile-avatar-circle">
                {getInitials(profile.name)}
              </div>
              <div className="profile-title-text">
                <h3>{profile.name || 'N/A'}</h3>
                <span>USER_ID: 001</span>
              </div>
            </div>
            
            <div className="profile-details-grid">
              <div className="profile-info-block">
                <Mail size={16} />
                <div className="profile-info-content">
                  <label>Email Address</label>
                  <span>{profile.email || 'N/A'}</span>
                </div>
              </div>
              
              <div className="profile-info-block">
                <Phone size={16} />
                <div className="profile-info-content">
                  <label>Phone Number</label>
                  <span>{profile.phone || 'N/A'}</span>
                </div>
              </div>
              
              <div className="profile-info-block">
                <Calendar size={16} />
                <div className="profile-info-content">
                  <label>Date of Birth</label>
                  <span>{profile.dob || 'N/A'}</span>
                </div>
              </div>
              
              <div className="profile-info-block">
                <Sparkles size={16} />
                <div className="profile-info-content">
                  <label>Profile Bio</label>
                  <span>Active Member</span>
                </div>
              </div>
            </div>
            
            {profile.bio && (
              <div className="profile-bio-box">
                "{profile.bio}"
              </div>
            )}
          </div>
        ) : (
          <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)' }}>
            No profile data loaded.
          </div>
        )}
      </div>

      {/* 2. Hobbies Panel */}
      <div>
        <div className="section-header">
          <Award size={20} />
          <h2>Hobbies & Skill Levels</h2>
        </div>
        
        {hobbies && hobbies.length > 0 ? (
          <div className="hobbies-grid">
            {hobbies.map((h, i) => (
              <div className="hobby-card" key={i}>
                <span className="hobby-name">{h.name}</span>
                <span className={`hobby-badge ${h.skill_level?.toLowerCase() || 'beginner'}`}>
                  {h.skill_level || 'Beginner'}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)', backgroundColor: 'var(--bg-tertiary)', borderRadius: '10px' }}>
            No hobbies recorded.
          </div>
        )}
      </div>

      {/* 3. Scheduled Events Panel */}
      <div>
        <div className="section-header">
          <Calendar size={20} />
          <h2>Scheduled Events</h2>
        </div>
        
        {events && events.length > 0 ? (
          <div className="events-list">
            {events.map((e, i) => (
              <div className="event-item" key={i}>
                <div className="event-details">
                  <span className="event-title">{e.title}</span>
                  <div className="event-meta">
                    <span>
                      <Calendar size={13} /> {e.date}
                    </span>
                    <span>
                      <MapPin size={13} /> {e.location}
                    </span>
                  </div>
                </div>
                <span className="event-id-badge">ID: {e.id}</span>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)', backgroundColor: 'var(--bg-tertiary)', borderRadius: '10px' }}>
            No events scheduled.
          </div>
        )}
      </div>

      {/* 4. Settings Panel */}
      <div>
        <div className="section-header">
          <Clock size={20} />
          <h2>System Preferences</h2>
        </div>
        
        {settings ? (
          <div className="settings-grid">
            {/* Theme */}
            <div className="setting-card">
              <div className="setting-icon-box">
                {settings.theme === 'light' ? <Sun size={18} /> : <Moon size={18} />}
              </div>
              <div className="setting-info">
                <span className="setting-label">Theme Mode</span>
                <span className={`setting-value theme-${settings.theme || 'light'}`}>
                  {settings.theme === 'light' ? '☀️ Light' : '🌙 Dark'}
                </span>
              </div>
            </div>
            
            {/* Language */}
            <div className="setting-card">
              <div className="setting-icon-box">
                <Globe size={18} />
              </div>
              <div className="setting-info">
                <span className="setting-label">Language</span>
                <span className="setting-value">🌐 {settings.language || 'English'}</span>
              </div>
            </div>
            
            {/* Notifications */}
            <div className="setting-card">
              <div className="setting-icon-box">
                {settings.notifications === 'on' ? <Bell size={18} /> : <BellOff size={18} />}
              </div>
              <div className="setting-info">
                <span className="setting-label">Notifications</span>
                <span className={`setting-value notif-${settings.notifications || 'off'}`}>
                  {settings.notifications === 'on' ? '🔔 Enabled' : '🔕 Muted'}
                </span>
              </div>
            </div>
            
            {/* Timezone */}
            <div className="setting-card">
              <div className="setting-icon-box">
                <Clock size={18} />
              </div>
              <div className="setting-info">
                <span className="setting-label">Timezone</span>
                <span className="setting-value">🕒 {settings.timezone || 'America/New_York'}</span>
              </div>
            </div>
          </div>
        ) : (
          <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)', backgroundColor: 'var(--bg-tertiary)', borderRadius: '10px' }}>
            No preferences available.
          </div>
        )}
      </div>
    </div>
  );
}
