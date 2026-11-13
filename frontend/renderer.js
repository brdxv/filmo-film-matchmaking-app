const API = window.FILMO_CONFIG.apiBase;
let currentUser = JSON.parse(localStorage.getItem("filmo_user") || "null");
let currentPage = "Discover";
let selectedPostFile = null;
let selectedInstantFile = null;
let selectedProfilePhotoFile = null;
let selectedReviewMedia = null;
let reviewRating = 0;
let reviewFilter = "all";
let peopleCards = [];
let peopleIndex = 0;
let historyStack = JSON.parse(localStorage.getItem("filmo_history") || "[]");
let historyIndex = Number(localStorage.getItem("filmo_history_index") || "-1");
let instantStories = [];
let instantIndex = 0;

const staticUrl = path => `${API}/static/${path}`;

function getResourceAlternatives(path) {
  if (!path) return [];

  const exts = [".png", ".jpg", ".jpeg", ".webp", ".gif"];
  const lower = String(path).toLowerCase();
  const current = exts.find(ext => lower.endsWith(ext));

  if (!current) return [];

  const base = path.slice(0, -current.length);

  return exts
    .filter(ext => ext !== current)
    .map(ext => staticUrl(`${base}${ext}`));
}

function handleImageFallback(img) {
  const raw = img.dataset.fallbacks || "[]";
  let fallbacks = [];

  try {
    fallbacks = JSON.parse(raw);
  } catch (err) {
    fallbacks = [];
  }

  const next = fallbacks.shift();

  if (!next) {
    img.onerror = null;
    return;
  }

  img.dataset.fallbacks = JSON.stringify(fallbacks);
  img.src = next;
}

function imageSrc(path) {
  const url = staticUrl(path || "");
  const fallbacks = getResourceAlternatives(path);

  if (!fallbacks.length) {
    return `src="${url}"`;
  }

  return `src="${url}" data-fallbacks='${JSON.stringify(fallbacks)}' onerror="handleImageFallback(this)"`;
}
async function api(path, options = {}) {
  const headers = options.body instanceof FormData ? {} : { "Content-Type": "application/json" };
  const res = await fetch(`${API}${path}`, { headers, ...options });
  const raw = await res.text();

  let data;
  try {
    data = raw ? JSON.parse(raw) : {};
  } catch (err) {
    const shortRaw = raw ? raw.slice(0, 180) : "No response body";
    throw new Error(`Server returned a non-JSON response. ${shortRaw}`);
  }

  if (!res.ok) throw new Error(data.message || "Request failed");
  return data;
}
function esc(v="") { return String(v).replace(/[&<>"']/g, s => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[s])); }
function setUser(user){ currentUser=user; localStorage.setItem("filmo_user", JSON.stringify(user)); }
function pushHistory(page, payload=null){
  const item={page,payload};
  if(historyIndex>=0 && JSON.stringify(historyStack[historyIndex])===JSON.stringify(item)) return;
  historyStack=historyStack.slice(0,historyIndex+1); historyStack.push(item); if(historyStack.length>40) historyStack.shift(); historyIndex=historyStack.length-1;
  localStorage.setItem("filmo_history",JSON.stringify(historyStack)); localStorage.setItem("filmo_history_index",String(historyIndex));
}

function truncateText(text, maxLength = 38) {
  if (!text) return "";
  const value = String(text);
  return value.length > maxLength ? value.slice(0, maxLength).trim() + "..." : value;
}

async function goBack(){ if(historyIndex>0){ historyIndex--; localStorage.setItem("filmo_history_index",String(historyIndex)); await route(historyStack[historyIndex],false); } }
async function goForward(){ if(historyIndex<historyStack.length-1){ historyIndex++; localStorage.setItem("filmo_history_index",String(historyIndex)); await route(historyStack[historyIndex],false); } }
async function route(item,push=false){ if(!item)return; if(item.page==="Media")return renderMediaDetail(item.payload.type,item.payload.id,push); if(item.page==="Chat")return renderChatPage(item.payload.mid,item.payload.name,push); if(item.page==="Instants")return renderInstantViewer(item.payload.targetId,push); return navigate(item.page,push); }
function appShell(content){
  const pages=["Profile","Discover","People","Liked You","Chats","Reviews"];
  document.querySelector("#app").innerHTML=`<div class="shell"><aside class="nav"><div class="nav-title">FILMO</div>${pages.map(p=>`<button class="${currentPage===p?'active':''}" onclick="navigate('${p}')">${p==='Liked You'?'Likes':p}</button>`).join('')}<button class="logout" onclick="logout()">Logout</button></aside><main class="main"><header class="topbar"><div><p class="eyebrow">FILMO</p><h1>${esc(currentPage)}</h1></div><div class="avatar-wrap"><img draggable="false" class="avatar" onclick="handleAvatar()" ${imageSrc(currentUser.profile_image||'Resources/Images/Profiles/ian_pfp.png')}/><div class="profile-menu" id="profileMenu"><button onclick="navigate('Profile')">Profile</button><button onclick="openAccountSettings()">Account Settings</button><button onclick="logout()">Logout</button></div></div></header><section id="page">${content}</section></main><div class="android-nav"><button onclick="goBack()"><img src="${staticUrl('Resources/Images/Icons/back_icon.png')}"/></button><button onclick="goForward()"><img src="${staticUrl('Resources/Images/Icons/forward_icon.png')}"/></button></div></div>`;
}
function handleAvatar(){ if(innerWidth<=760 && currentPage==="Profile"){ const m=document.querySelector('#profileMenu'); m.style.display=m.style.display==='block'?'none':'block'; } else navigate('Profile'); }
function posterGrid(title,items,type){ return `<h3>${title}</h3><div class="poster-row">${items.map(x=>`<div class="poster" onclick="event.stopPropagation(); renderMediaDetail('${type}',${x.id})"><img draggable="false" ${imageSrc(x.poster_path)} title="${esc(x.title)}"/><span>${x.ranking}</span></div>`).join('')}</div>`; }
function section(title,text){ return `<div class="section"><h3>${title}</h3><p>${esc(text||'Not set yet.')}</p></div>`; }

function openAccountSettings(){
  const menu=document.querySelector('#profileMenu');
  if(menu) menu.style.display='none';
  modal(`<h2>Account Settings</h2><p class="muted">Update your username or change your password.</p>
  <label>Username</label><input id="account_username" value="${esc(currentUser.username||'')}"/>
  <label>Current Password</label><div class="password-wrap"><input id="account_current_password" type="password" placeholder="Required only when changing password"/><button class="eye-btn" onclick="togglePassword('account_current_password',this)"><img src="${staticUrl('Resources/Images/Icons/eye_icon.png')}"/></button></div>
  <label>New Password</label><div class="password-wrap"><input id="account_new_password" type="password" placeholder="Leave blank to keep current password"/><button class="eye-btn" onclick="togglePassword('account_new_password',this)"><img src="${staticUrl('Resources/Images/Icons/eye_icon.png')}"/></button></div>
  <label>Confirm New Password</label><div class="password-wrap"><input id="account_confirm_password" type="password" placeholder="Retype new password"/><button class="eye-btn" onclick="togglePassword('account_confirm_password',this)"><img src="${staticUrl('Resources/Images/Icons/eye_icon.png')}"/></button></div>
  <button class="primary" onclick="saveAccountSettings()">Save Account Settings</button><button class="secondary" onclick="closeModal()">Cancel</button>`);
}
async function saveAccountSettings(){
  const username=document.querySelector('#account_username').value.trim();
  const current_password=document.querySelector('#account_current_password').value;
  const new_password=document.querySelector('#account_new_password').value;
  const confirm_password=document.querySelector('#account_confirm_password').value;
  if(!username) return alert('Username is required.');
  if(new_password && new_password!==confirm_password) return alert('New passwords do not match.');
  const d=await api(`/api/account/${currentUser.id}`,{method:'PUT',body:JSON.stringify({username,current_password,new_password})});
  setUser(d.user); closeModal(); alert('Account settings updated.'); navigate('Profile');
}

function modal(content){ document.querySelector('#modalBackdrop')?.remove(); const el=document.createElement('div'); el.className='modal-backdrop'; el.id='modalBackdrop'; el.innerHTML=`<div class="modal">${content}</div>`; document.body.appendChild(el); }
function closeModal(){ document.querySelector('#modalBackdrop')?.remove(); }
async function renderLogin(){
  document.querySelector('#app').innerHTML=`<div class="auth"><section class="hero"><p class="eyebrow">Match through cinema</p><div class="logo">FILMO</div><p>A matchmaking app for film lovers.</p></section><section class="auth-card"><h1>Welcome back</h1><p class="muted">Sample accounts: ian, mika, leo, ara. Password: password</p><label>Username</label><input id="username" placeholder="ian"/><label>Password</label><div class="password-wrap"><input id="password" type="password" placeholder="password"/><button class="eye-btn" onclick="togglePassword('password',this)"><img src="${staticUrl('Resources/Images/Icons/eye_icon.png')}"/></button></div><button class="primary" onclick="login()">Log In</button><button class="secondary" onclick="renderRegister()">Create Account</button></section></div>`;
  setTimeout(()=>document.querySelector('#username')?.focus(),100);
}
function togglePassword(id,btn){ const input=document.querySelector('#'+id); const show=input.type==='password'; input.type=show?'text':'password'; btn.querySelector('img').src=staticUrl(show?'Resources/Images/Icons/eye_off_icon.png':'Resources/Images/Icons/eye_icon.png'); input.focus(); }

async function renderRegister() {
  document.querySelector("#app").innerHTML = `
    <div class="auth">
      <section class="hero">
        <p class="eyebrow">Join FILMO</p>
        <h1>Create your account</h1>
        <p>Start with your username, password, and optional profile photo. You can complete your profile details after logging in.</p>
      </section>

      <section class="auth-card">
        <h1>Create Account</h1>

        <label>Username</label>
        <input id="reg_username" placeholder="Choose a username" autocomplete="username" />

        <label>Password</label>
        <div class="password-wrap">
          <input id="reg_password" type="password" placeholder="Create a password" autocomplete="new-password" />
          <button class="eye-btn" onclick="togglePassword('reg_password', this)">
            <img src="${staticUrl('Resources/Images/Icons/eye_icon.png')}" />
          </button>
        </div>

        <label>Confirm Password</label>
        <div class="password-wrap">
          <input id="reg_confirm_password" type="password" placeholder="Retype your password" autocomplete="new-password" />
          <button class="eye-btn" onclick="togglePassword('reg_confirm_password', this)">
            <img src="${staticUrl('Resources/Images/Icons/eye_icon.png')}" />
          </button>
        </div>

        <div class="file-chip">
          <button class="secondary" onclick="document.querySelector('#reg_profile_photo').click()">Add Profile Photo</button>
          <span id="reg_profile_label" class="muted">Optional. You can add this later.</span>
          <input hidden id="reg_profile_photo" type="file" accept=".png,.jpg,.jpeg" onchange="selectRegisterProfilePhoto(event)" />
        </div>

        <button class="primary" onclick="register()">Create Account</button>
        <button class="secondary" onclick="renderLogin()">Back to Login</button>
      </section>
    </div>
  `;

  setTimeout(() => document.querySelector("#reg_username")?.focus(), 80);
}

let selectedRegisterProfilePhoto = null;

function selectRegisterProfilePhoto(event) {
  selectedRegisterProfilePhoto = event.target.files[0] || null;
  const label = document.querySelector("#reg_profile_label");
  if (label) {
    label.textContent = selectedRegisterProfilePhoto
      ? selectedRegisterProfilePhoto.name
      : "Optional. You can add this later.";
  }
}

async function login(){ try{ const data=await api('/api/login',{method:'POST',body:JSON.stringify({username:username.value,password:password.value})}); const u=await api(`/api/user/${data.user.id}`); setUser(u.user); historyStack=[]; historyIndex=-1; navigate('Discover'); }catch(e){ alert(e.message); setTimeout(()=>{ (username.value?password:username).focus(); },100); } }

async function register() {
  try {
    const username = document.querySelector("#reg_username").value.trim();
    const password = document.querySelector("#reg_password").value;
    const confirm = document.querySelector("#reg_confirm_password").value;

    if (!username || !password) {
      alert("Please enter a username and password.");
      return;
    }

    if (password !== confirm) {
      alert("Passwords do not match.");
      document.querySelector("#reg_confirm_password")?.focus();
      return;
    }

    const form = new FormData();
    form.append("username", username);
    form.append("password", password);

    if (selectedRegisterProfilePhoto) {
      form.append("profile_photo", selectedRegisterProfilePhoto);
    }

    await api("/api/register", {
      method: "POST",
      body: form
    });

    selectedRegisterProfilePhoto = null;
    alert("Account created. You can now log in.");
    renderLogin();
  } catch (err) {
    alert(err.message);
  }
}

function logout(){ localStorage.removeItem('filmo_user'); currentUser=null; renderLogin(); }
async function navigate(page,push=true){ currentPage=page; if(push)pushHistory(page); await ({Profile:renderProfile,Discover:renderDiscover,People:renderPeople,'Liked You':renderLikedYou,Chats:renderChats,Reviews:renderReviews}[page])(); }
async function refreshUser(){ const d=await api(`/api/user/${currentUser.id}`); setUser(d.user); return d; }
async function renderProfile(){ const d=await refreshUser(); const c=await api(`/api/user/${currentUser.id}/content?viewer_id=${currentUser.id}`); appShell(`<article class="card"><div class="profile-cover"><img draggable="false" ${imageSrc(d.user.profile_image)}/><div class="profile-overlay"><h2>${esc(d.user.display_name)}</h2><p>@${esc(d.user.username)} · ${esc(d.user.location)}</p></div></div><div class="stats"><div class="stat" onclick="scrollToActivity('posts')"><strong>${d.counts.posts}</strong><span>Posts</span></div><div class="stat" onclick="scrollToActivity('reviews')"><strong>${d.counts.reviews}</strong><span>Reviews</span></div><div class="stat"><strong>${d.counts.matches}</strong><span>Matches</span></div></div>${posterGrid('Top 4 Movies',d.top_movies,'movie')}${posterGrid('Top 4 TV Shows',d.top_tv,'tv')}${section('My Bio',d.user.bio)}${section('Things We Can Talk About',d.user.talk_about)}<div class="grid-two">${section('Film / TV Taste',d.user.taste_summary)}${section("I'm Looking For",d.user.looking_for)}</div>${section('My Interests',d.user.hobbies)}<button class="primary" onclick="openEditProfile()">Edit Profile</button>
      <div class="profile-photo-uploader">
        <button class="secondary" onclick="document.querySelector('#profile_photo_input').click()">Choose New Profile Photo</button>
        <span class="muted" id="profile_photo_label">No new profile photo selected.</span>
        <input hidden id="profile_photo_input" type="file" accept=".png,.jpg,.jpeg" onchange="selectProfilePhoto(event)" />
        <button class="primary profile-photo-save" id="profile_photo_save" style="display:none" onclick="saveProfilePhoto()">Save Profile Photo</button>
      </div></article><article class="card" id="profile-content"><h2>Profile Activity</h2><div class="content-toggle"><button class="pill active" id="toggle_posts" onclick="showProfileSection('posts')">Posts</button><button class="pill" id="toggle_reviews" onclick="showProfileSection('reviews')">Reviews</button></div><div id="profile-posts">${c.posts.length?c.posts.map(postCard).join(''):'<p class="muted">No posts yet.</p>'}</div><div id="profile-reviews" style="display:none">${c.reviews.length?c.reviews.map(reviewCard).join(''):'<p class="muted">No reviews yet.</p>'}</div></article>`); }
function scrollToActivity(type){ showProfileSection(type); document.querySelector('#profile-content')?.scrollIntoView({behavior:'smooth'}); }
function showProfileSection(type){ const p=document.querySelector('#profile-posts'), r=document.querySelector('#profile-reviews'); if(!p||!r)return; p.style.display=type==='posts'?'block':'none'; r.style.display=type==='reviews'?'block':'none'; document.querySelector('#toggle_posts')?.classList.toggle('active',type==='posts'); document.querySelector('#toggle_reviews')?.classList.toggle('active',type==='reviews'); }

function selectProfilePhoto(event) {
  selectedProfilePhotoFile = event.target.files[0] || null;
  const label = document.querySelector("#profile_photo_label");
  const saveBtn = document.querySelector("#profile_photo_save");

  if (!selectedProfilePhotoFile) {
    if (label) label.textContent = "No new profile photo selected.";
    if (saveBtn) saveBtn.style.display = "none";
    return;
  }

  const allowed = [".png", ".jpg", ".jpeg"];
  const lower = selectedProfilePhotoFile.name.toLowerCase();
  const ok = allowed.some(ext => lower.endsWith(ext));

  if (!ok) {
    alert("Please choose a PNG, JPG, or JPEG image only.");
    event.target.value = "";
    selectedProfilePhotoFile = null;
    if (label) label.textContent = "Invalid file type. Choose PNG, JPG, or JPEG.";
    if (saveBtn) saveBtn.style.display = "none";
    return;
  }

  if (label) label.textContent = `Selected: ${selectedProfilePhotoFile.name}`;
  if (saveBtn) saveBtn.style.display = "inline-flex";
}

async function saveProfilePhoto() {
  if (!selectedProfilePhotoFile) return alert("Please choose a profile photo first.");

  const label = document.querySelector("#profile_photo_label");
  const saveBtn = document.querySelector("#profile_photo_save");
  if (label) label.textContent = `Uploading ${selectedProfilePhotoFile.name}...`;
  if (saveBtn) saveBtn.disabled = true;

  const form = new FormData();
  form.append("profile_photo", selectedProfilePhotoFile);

  try {
    const data = await api(`/api/user/${currentUser.id}/profile-photo`, {
      method: "POST",
      body: form
    });

    selectedProfilePhotoFile = null;
    setUser(data.user);
    alert("Profile photo updated.");
    renderProfile();
  } catch (err) {
    alert(err.message);
    if (label) label.textContent = "Upload failed. Please try again.";
    if (saveBtn) saveBtn.disabled = false;
  }
}


function openEditProfile(){ modal(`<h2>Edit Profile</h2>${['display_name','bio','location','taste_summary','talk_about','looking_for','hobbies'].map(f=>`<label>${f.replaceAll('_',' ')}</label><input id="edit_${f}" value="${esc(currentUser[f]||'')}"/>`).join('')}<div class="grid-two"><button class="secondary" onclick="openTopEditor('movie')">Edit Top 4 Movies</button><button class="secondary" onclick="openTopEditor('tv')">Edit Top 4 TV Shows</button></div><button class="primary" onclick="saveProfile()">Save Changes</button><button class="secondary" onclick="closeModal()">Cancel</button>`); }
async function saveProfile(){ const p={}; ['display_name','bio','location','taste_summary','talk_about','looking_for','hobbies'].forEach(f=>p[f]=document.querySelector('#edit_'+f).value); await api(`/api/user/${currentUser.id}`,{method:'PUT',body:JSON.stringify(p)}); closeModal(); renderProfile(); }
async function openTopEditor(type){ closeModal(); const d=await api(`/api/user/${currentUser.id}`); const items=type==='movie'?d.top_movies:d.top_tv; modal(`<h2>Edit Top 4 ${type==='movie'?'Movies':'TV Shows'}</h2><div id="top_selected" data-type="${type}" data-items='${JSON.stringify(items).replaceAll("'","&apos;")}'>${renderTopSelected(items)}</div><div class="search-row"><input id="top_search" placeholder="Search..." oninput="searchTopMedia('${type}')"/><button class="primary" onclick="saveTopMedia('${type}')">Save</button></div><div id="top_results" class="search-results"></div><button class="secondary" onclick="closeModal()">Close</button>`); }
function renderTopSelected(items){ return `<div class="poster-row">${items.map((x,i)=>`<div class="poster" onclick="removeTopItem(${x.id})"><img draggable="false" ${imageSrc(x.poster_path)}/><span>${i+1}</span><span class="remove-x">×</span></div>`).join('')}</div><p class="muted">Click a poster to remove it. Add titles from search below.</p>`; }
function topItems(){ try { return JSON.parse((document.querySelector('#top_selected').dataset.items||'[]').replaceAll('&apos;', "'")); } catch(e){ return []; } }
function setTopItems(items){ document.querySelector('#top_selected').dataset.items=JSON.stringify(items.slice(0,4)); top_selected.innerHTML=renderTopSelected(items.slice(0,4).map((x,i)=>({...x,ranking:i+1}))); }
function topIds(){ return topItems().map(x=>Number(x.id)).filter(Boolean); }
async function searchTopMedia(type){ const q=top_search.value.trim(); if(!q){top_results.innerHTML='';return;} const d=await api(`/api/search-media?q=${encodeURIComponent(q)}&type=${type}`); top_results.innerHTML=d.results.map(x=>`<div class="search-item"><img ${imageSrc(x.poster_path)}/><div><strong>${esc(x.title)}</strong><div class="muted">${x.media_type} · ${x.year}</div></div><button class="secondary" onclick='addTopItem(${JSON.stringify(x).replaceAll("'","&apos;")})'>Add</button></div>`).join(''); }
function addTopItem(x){ let items=topItems(); if(items.some(item=>Number(item.id)===Number(x.id)))return; if(items.length>=4)return alert('Top 4 can only contain four titles.'); items.push(x); setTopItems(items); }
function removeTopItem(id){ let items=topItems().filter(x=>Number(x.id)!==Number(id)); setTopItems(items); }
async function saveTopMedia(type){ await api(`/api/top-media/${currentUser.id}`,{method:'PUT',body:JSON.stringify({media_type:type,ids:topIds()})}); alert('Top 4 updated.'); closeModal(); renderProfile(); }
async function renderDiscover(){ const d=await api(`/api/feed/${currentUser.id}`); appShell(`<article class="card"><textarea id="post_content" placeholder="Share a film thought, review snippet, or watch update..."></textarea><div class="file-chip"><button class="secondary" onclick="post_media.click()">📷 Add photo/video</button><span id="post_file_label" class="muted">No file selected</span><input hidden id="post_media" type="file" accept="image/*,video/*" onchange="selectPostFile(event)"/></div><button class="primary" onclick="createPost()">Post</button></article><div id="feed-list">${d.posts.map(postCard).join('')}</div>`); }
function selectPostFile(e){ selectedPostFile=e.target.files[0]||null; post_file_label.textContent=selectedPostFile?selectedPostFile.name:'No file selected'; }
function mediaBlock(x){ if(!x.media_path)return''; if(x.media_type==='video'){ const id='video-'+x.id; return `<div class="video-wrap"><video id="${id}" src="${staticUrl(x.media_path)}" muted></video><div class="video-controls"><button onclick="videoSeek('${id}',-5)"><img src="${staticUrl('Resources/Images/Icons/rewind_icon.png')}"/></button><button onclick="videoToggle('${id}')"><img src="${staticUrl('Resources/Images/Icons/play_icon.png')}"/></button><button onclick="videoSeek('${id}',5)"><img src="${staticUrl('Resources/Images/Icons/forward5_icon.png')}"/></button></div></div>`;} return `<img draggable="false" class="media" ${imageSrc(x.media_path)}/>`; }
function videoToggle(id){ const v=document.getElementById(id); if(v) v.paused?v.play():v.pause(); }
function videoSeek(id,sec){ const v=document.getElementById(id); if(v)v.currentTime=Math.max(0,v.currentTime+sec); }
function postCard(p){ return `<article class="card" id="post-${p.id}"><div class="user-row"><img draggable="false" ${imageSrc(p.profile_image)}/><div><strong>${esc(p.display_name)}</strong><div class="muted">@${esc(p.username)} · ${esc(p.created_at)}</div></div></div><p>${esc(p.content)}</p>${mediaBlock(p)}<div class="actions"><button id="post-like-${p.id}" class="pill ${p.liked_by_me?'active':''}" onclick="togglePostLike(${p.id})">♥ ${p.like_count}</button><button id="post-comment-btn-${p.id}" class="pill" onclick="openComments(${p.id})">💬 ${p.comment_count}</button>${p.user_id===currentUser.id?`<button class="pill danger" onclick="deletePost(${p.id})">Delete</button>`:''}</div></article>`; }
async function createPost(){ const content=post_content.value.trim(); if(!content&&!selectedPostFile)return alert('Please write something or attach media.'); const form=new FormData(); form.append('user_id',currentUser.id); form.append('content',content); if(selectedPostFile)form.append('media',selectedPostFile); await api('/api/post',{method:'POST',body:form}); selectedPostFile=null; renderDiscover(); }
async function togglePostLike(id){ const d=await api(`/api/post/${id}/like`,{method:'POST',body:JSON.stringify({user_id:currentUser.id})}); const b=document.querySelector(`#post-like-${id}`); if(b){b.textContent=`♥ ${d.like_count}`; b.classList.toggle('active',d.liked);} }
async function deletePost(id){ if(!confirm('Delete this post?'))return; await api(`/api/post/${id}?user_id=${currentUser.id}`,{method:'DELETE'}); document.querySelector(`#post-${id}`)?.remove(); }
async function openComments(id){ const d=await api(`/api/post/${id}/comments`); modal(`<h2>Comments</h2>${d.comments.map(c=>`<div class="section"><strong>${esc(c.display_name)}:</strong> ${esc(c.comment_text)}</div>`).join('')||'<p class="muted">No comments yet.</p>'}<input id="comment_text" placeholder="Write a comment..."/><button class="primary" onclick="addComment(${id})">Send</button><button class="secondary" onclick="closeModal()">Close</button>`); }
async function addComment(id){ if(!comment_text.value.trim())return; const d=await api(`/api/post/${id}/comments`,{method:'POST',body:JSON.stringify({user_id:currentUser.id,comment_text:comment_text.value.trim()})}); const b=document.querySelector(`#post-comment-btn-${id}`); if(b)b.textContent=`💬 ${d.comment_count}`; closeModal(); }
async function renderPeople(){ const d=await api(`/api/people/${currentUser.id}`); peopleCards=d.cards; peopleIndex=0; appShell(`<div class="match-viewport" id="matchViewport">${currentPeopleCard()}</div>`); attachSwipe(); }
function currentPeopleCard(){ if(!peopleCards.length||peopleIndex>=peopleCards.length)return `<article class="card"><h2>No more profiles for now</h2><p class="muted">Try again after more users register.</p></article>`; const i=peopleCards[peopleIndex],u=i.user; return `<article class="card match-card-single" id="activeMatchCard"><div class="match-hero"><img draggable="false" ${imageSrc(u.profile_image)}/><div class="match-badge">${i.score}% · ${i.compatibility_label}</div></div><h2>${esc(u.display_name)}</h2><p class="muted">@${esc(u.username)} · ${i.shared_count}/8 shared top titles</p>${posterGrid('Top 4 Movies',i.top_movies,'movie')}${posterGrid('Top 4 TV Shows',i.top_tv,'tv')}${section('My Bio',u.bio)}${section('Things We Can Talk About',u.talk_about)}<div class="grid-two">${section("I'm Looking For",u.looking_for)}${section('Film / TV Taste',u.taste_summary)}</div>${section('My Interests',u.hobbies)}<div class="match-actions one-send"><input id="match_msg_${u.id}" placeholder="Leave a short message before matching..."/><button class="icon-circle" onclick="sendMatch(${u.id},true)"><img src="${staticUrl('Resources/Images/Icons/send_icon.png')}"/></button></div><div class="actions" style="justify-content:center;margin-top:12px"><button class="icon-circle" onclick="event.stopPropagation(); rejectCurrent()"><img src="${staticUrl('Resources/Images/Icons/x_icon.png')}"/></button><button class="icon-circle" onclick="sendMatch(${u.id},true)"><img src="${staticUrl('Resources/Images/Icons/heart_icon.png')}"/></button></div></article>`; }
function attachSwipe(){ const card=document.querySelector('#activeMatchCard'); if(!card)return; let sx=0,dx=0,drag=false; const interactive=t=>t.closest('button,input,textarea,select,.poster,a'); card.addEventListener('pointerdown',e=>{ if(interactive(e.target))return; drag=true;sx=e.clientX;card.setPointerCapture(e.pointerId);}); card.addEventListener('pointermove',e=>{if(!drag)return;dx=e.clientX-sx;card.style.transform=`translateX(${dx}px) rotate(${dx/25}deg)`;}); card.addEventListener('pointerup',()=>{if(!drag)return;drag=false;if(dx>110)sendMatch(peopleCards[peopleIndex].user.id,true);else if(dx<-110)rejectCurrent();else card.style.transform='';dx=0;}); }
function nextCard(){ peopleIndex++; matchViewport.innerHTML=currentPeopleCard(); attachSwipe(); }
function rejectCurrent(){ activeMatchCard?.classList.add('swipe-left'); setTimeout(nextCard,220); }
async function sendMatch(id,silent=false){ const message=document.querySelector(`#match_msg_${id}`)?.value||''; const d=await api('/api/match/request',{method:'POST',body:JSON.stringify({sender_id:currentUser.id,receiver_id:id,message})}); if(!silent)alert(d.status==='matched'?'It is a match! You can now chat.':'Match request sent.'); activeMatchCard?.classList.add('swipe-right'); setTimeout(nextCard,220); }
async function renderLikedYou(){ const d=await api(`/api/liked-you/${currentUser.id}`); appShell(d.requests.length?d.requests.map(r=>`<article class="card"><div class="user-row"><img ${imageSrc(r.profile_image)}/><div><strong>${esc(r.display_name)}</strong><div class="muted">@${esc(r.username)} · ${esc(r.location)}</div></div></div><p>${esc(r.bio)}</p><p><strong>Film / TV Taste:</strong> ${esc(r.taste_summary)}</p>${r.message?`<div class="note">“${esc(r.message)}”</div>`:''}<div class="actions"><button class="pill" onclick="respondMatch(${r.id},'decline')">× Decline</button><button class="pill active" onclick="respondMatch(${r.id},'accept')">♥ Accept</button></div></article>`).join(''):`<article class="card"><h2>No likes yet</h2><p class="muted">Match requests sent to you will appear here.</p></article>`); }
async function respondMatch(id,action){ await api('/api/match/respond',{method:'POST',body:JSON.stringify({request_id:id,user_id:currentUser.id,action})}); renderLikedYou(); }
async function renderChats(){ const d=await api(`/api/chats/${currentUser.id}`); const inst=await api(`/api/instants/${currentUser.id}`); appShell(`<article class="card"><h2>Instants</h2><div class="story-row"><div class="story ${inst.me?.has_instant?'has-instant':''}" onclick="${inst.me?.has_instant?`renderInstantViewer(${currentUser.id})`:`openCreateInstant()`}"><img ${imageSrc(inst.me?.profile_image||currentUser.profile_image)}/><span>${inst.me?.has_instant?'Your Instant':'Add Instant'}</span></div>${inst.instant_users.map(u=>`<div class="story ${u.has_instant?'has-instant':''}" onclick="${u.has_instant?`renderInstantViewer(${u.id})`:''}"><img ${imageSrc(u.profile_image)}/><span>${esc(u.display_name)}</span></div>`).join('')}</div></article>${d.matches.length?d.matches.map(m=>`<div class="chat-row" onclick="renderChatPage(${m.id}, '${esc(m.other_name)}')"><img ${imageSrc(m.other_image)}/><div><strong>${esc(m.other_name)}</strong><div class="muted">${esc(m.latest_message||'Start or continue the conversation')}</div></div></div>`).join(''):`<article class="card"><h2>No matches yet</h2><p class="muted">Accept or send match requests to start chatting.</p></article>`}`); }
function openCreateInstant(){ modal(`<h2>Create Instant</h2><textarea id="instant_content" placeholder="Say something about this instant..."></textarea><div class="file-chip"><button class="secondary" onclick="instant_media.click()">📷 Add image/video</button><span id="instant_file_label" class="muted">No file selected</span><input hidden id="instant_media" type="file" accept="image/*,video/*" onchange="selectInstantFile(event)"/></div><button class="primary" onclick="createInstant()">Post Instant</button><button class="secondary" onclick="closeModal()">Cancel</button>`); }
function selectInstantFile(e){ selectedInstantFile=e.target.files[0]||null; instant_file_label.textContent=selectedInstantFile?selectedInstantFile.name:'No file selected'; }
async function createInstant(){ const form=new FormData(); form.append('user_id',currentUser.id); form.append('content',instant_content.value.trim()); if(selectedInstantFile)form.append('media',selectedInstantFile); await api('/api/instant',{method:'POST',body:form}); selectedInstantFile=null; closeModal(); renderChats(); }
async function renderInstantViewer(targetId,push=true){
  currentPage='Instants'; if(push)pushHistory('Instants',{targetId});
  const inst=await api(`/api/instants/${currentUser.id}`);
  const sequence=[];
  if(targetId===currentUser.id) sequence.push(currentUser.id);
  else { sequence.push(targetId); inst.instant_users.forEach(u=>{ if(u.has_instant && u.id!==targetId) sequence.push(u.id); }); }
  instantStories=[];
  for(const uid of sequence){ const d=await api(`/api/instants/${currentUser.id}/${uid}`); instantStories.push(...d.stories); }
  instantIndex=0; appShell(instantScreen()); attachInstantSwipe();
}
function instantScreen(){
  const visible=instantStories.slice(instantIndex,instantIndex+3).reverse(); const cur=instantStories[instantIndex]; const mine=cur&&cur.user_id===currentUser.id;
  return `<section class="instant-screen"><button class="instant-back secondary" onclick="navigate('Chats')">← Back</button><div class="instant-top-actions">${mine?`<button title="Archive" onclick="archiveCurrentInstant(${cur?cur.id:0})">Archive</button><button title="Delete" onclick="deleteCurrentInstant(${cur?cur.id:0})">Delete</button><button title="Archive List" onclick="openInstantArchive()"><img src="${staticUrl('Resources/Images/Icons/archive_icon.png')}"/></button>`:''}</div><div class="instant-stack" id="instantStack">${visible.map(s=>`<div class="instant-card">${s.media_type==='video'?`<video src="${staticUrl(s.media_path)}" autoplay muted loop></video>`:`<img ${imageSrc(s.media_path)}/>`}<div class="instant-text">${esc(s.content||'')}<br><small>${esc(s.display_name||'')} · active up to 24h</small></div></div>`).join('')||`<div class="instant-card"><div class="instant-text">No instant available.</div></div>`}</div>${mine?`<div class="reactions"><div class="react" style="left:42%;top:10px" onclick="openCreateInstant()"><img src="${staticUrl('Resources/Images/Icons/camera_icon.png')}"/></div></div>`:`<div class="reactions">${[['heart_emoji.png','heart'],['laugh_emoji.png','laugh'],['vomit_emoji.png','vomit'],['fire_emoji.png','fire'],['plus_emoji.png','plus']].map(([img,val])=>`<div class="react" onclick="instantReact('${val}',${cur?cur.id:0},'${img}')"><img src="${staticUrl('Resources/Images/Emojis/'+img)}"/></div>`).join('')}</div>`}<div class="reply-bar"><input id="instant_reply" placeholder="${mine?'Leave a comment on your instant...':'Leave reply...'}"/><button onclick="replyToInstant(${cur?cur.id:0})"><img style="width:28px;height:28px;filter:invert(1)" src="${staticUrl('Resources/Images/Icons/send_icon.png')}"/></button></div></section>`;
}
function attachInstantSwipe(){ const st=document.querySelector('#instantStack'); if(!st)return; let sx=0,dx=0; st.addEventListener('pointerdown',e=>{sx=e.clientX;}); st.addEventListener('pointerup',e=>{dx=e.clientX-sx;if(Math.abs(dx)>60) nextInstant(dx<0?'left':'right');}); }
function nextInstant(direction='spin'){ const top=document.querySelector('.instant-card:last-child'); if(top){ const arr=direction==='left'?['fly-left','fly-spin']:['fly-right','fly-spin']; top.classList.add(arr[Math.floor(Math.random()*arr.length)]); } setTimeout(()=>{ if(instantIndex<instantStories.length-1)instantIndex++; else instantIndex=0; page.innerHTML=instantScreen(); attachInstantSwipe(); },420); }

async function archiveCurrentInstant(storyId) {
  if (!storyId) return;
  if (!confirm("Archive this instant? Only you will see it in your archive.")) return;
  await api(`/api/instant/${storyId}/archive`, {
    method: "POST",
    body: JSON.stringify({ user_id: currentUser.id })
  });
  alert("Instant archived.");
  renderChats();
}

async function deleteCurrentInstant(storyId) {
  if (!storyId) return;
  if (!confirm("Delete this instant permanently?")) return;
  await api(`/api/instant/${storyId}?user_id=${currentUser.id}`, { method: "DELETE" });
  alert("Instant deleted.");
  renderChats();
}

async function openInstantArchive(){ const d=await api(`/api/instants/archive/${currentUser.id}`); modal(`<h2>Instant Archive</h2><p class="muted">Only your expired instants are visible here.</p><div class="archive-list">${d.stories.length?d.stories.map(s=>`<div class="archive-item"><img ${imageSrc(s.media_path)}/><div><strong>${esc(s.content||'Archived instant')}</strong><div class="muted">${esc(s.created_at)}</div></div></div>`).join(''):'<p class="muted">No archived instants yet.</p>'}</div><button class="secondary" onclick="closeModal()">Close</button>`); }
async function instantReact(reaction,storyId,img){ if(reaction==='plus')return alert('Reaction customization placeholder.'); if(storyId)await api(`/api/instant/${storyId}/react`,{method:'POST',body:JSON.stringify({user_id:currentUser.id,reaction})}); const pop=document.createElement('div'); pop.className='reaction-pop'; pop.innerHTML=`<img src="${staticUrl('Resources/Images/Emojis/'+img)}"/>`; document.body.appendChild(pop); setTimeout(()=>pop.remove(),760); }
async function replyToInstant(storyId){ const input=document.querySelector('#instant_reply'); const text=input.value.trim(); if(!text||!storyId)return; await api(`/api/instant/${storyId}/reply`,{method:'POST',body:JSON.stringify({sender_id:currentUser.id,reply_text:text})}); input.value=''; const pop=document.createElement('div'); pop.className='reaction-pop'; pop.innerHTML=`<img src="${staticUrl('Resources/Images/Icons/send_icon.png')}"/>`; document.body.appendChild(pop); setTimeout(()=>pop.remove(),760); }
async function renderChatPage(mid,name,push=true){ currentPage=name; if(push)pushHistory('Chat',{mid,name}); const d=await api(`/api/messages/${mid}?user_id=${currentUser.id}`); appShell(`<section class="chat-page"><div class="message-list" id="messageList">${d.messages.map(m=>`<div class="message ${m.sender_id===currentUser.id?'mine':'theirs'}"><p>${esc(m.message_text)}</p><small>${esc(m.created_at)}</small></div>`).join('')||'<p class="muted">No messages yet.</p>'}</div><div class="message-form"><input id="message_text" placeholder="Send a message..."/><button class="primary" onclick="sendMessage(${mid}, '${esc(name)}')"><img style="width:20px;height:20px" src="${staticUrl('Resources/Images/Icons/send_icon.png')}"/></button></div></section>`); setTimeout(()=>{messageList.scrollTop=messageList.scrollHeight},0); }
async function sendMessage(mid,name){ if(!message_text.value.trim())return; await api(`/api/messages/${mid}`,{method:'POST',body:JSON.stringify({sender_id:currentUser.id,message_text:message_text.value.trim()})}); renderChatPage(mid,name,false); }
async function renderReviews(){ const d=await api(`/api/reviews/${currentUser.id}`); selectedReviewMedia=null; reviewRating=0; appShell(`<article class="card"><div class="search-row"><input id="review_search" placeholder="Search movies or TV shows..." oninput="searchReviewMedia()"/><button class="secondary" onclick="toggleReviewFilter()">☰</button></div><div id="review_filter" class="content-toggle" style="display:none"><button class="pill active" id="filter_all" onclick="setReviewFilter('all')">All</button><button class="pill" id="filter_movie" onclick="setReviewFilter('movie')">Movie</button><button class="pill" id="filter_tv" onclick="setReviewFilter('tv')">TV Show</button></div><div id="review_results" class="search-results"></div><div id="selected_review_media"></div><div class="star-row" id="star_row">${[1,2,3,4,5].map(i=>`<span class="star" onclick="setRating(${i})" ondblclick="setRating(${i-0.5})">★</span>`).join('')}</div><p class="muted" id="rating_text">Rating: 0/5. Click for full star, double-click for half.</p><textarea id="review_text" placeholder="Write your review..."></textarea><button class="primary" onclick="createReview()">Post Review</button></article><div id="reviews-list">${d.reviews.map(reviewCard).join('')}</div>`); }
function toggleReviewFilter(){ review_filter.style.display=review_filter.style.display==='none'?'flex':'none'; }
function setReviewFilter(type){ reviewFilter=type; ['all','movie','tv'].forEach(x=>document.querySelector(`#filter_${x}`)?.classList.toggle('active',x===type)); searchReviewMedia(); }
async function searchReviewMedia(){ const q=review_search.value.trim(); if(!q){review_results.innerHTML='';return;} const d=await api(`/api/search-media?q=${encodeURIComponent(q)}&type=${reviewFilter}`); review_results.innerHTML=d.results.map(x=>`<div class="search-item"><img onclick="renderMediaDetail('${x.media_type}',${x.id})" ${imageSrc(x.poster_path)}/><div><strong>${esc(x.title)}</strong><div class="muted">${x.media_type} · ${x.year}</div></div><button class="secondary" onclick='selectReviewMedia(${JSON.stringify(x)})'>Select</button></div>`).join(''); }
function selectReviewMedia(x){ selectedReviewMedia=x; selected_review_media.innerHTML=`<div class="selected-media"><button class="clear-selected" onclick="clearReviewMedia()">×</button><img onclick="renderMediaDetail('${x.media_type}',${x.id})" ${imageSrc(x.poster_path)}/><div><strong>${esc(x.title)}</strong><div class="muted">${x.media_type} · ${x.year}</div></div></div>`; }
function clearReviewMedia(){ selectedReviewMedia=null; selected_review_media.innerHTML=''; }
function setRating(v){ reviewRating=v; document.querySelectorAll('.star').forEach((s,i)=>{s.classList.toggle('full',i+1<=Math.floor(v));s.classList.toggle('half',i+0.5===v)}); rating_text.textContent=`Rating: ${v}/5`; }
async function createReview(){ const text=review_text.value.trim(); if(!selectedReviewMedia)return alert('Search and select a movie or TV show first.'); if(!reviewRating)return alert('Select a rating first.'); if(!text)return alert('Please write a review.'); await api('/api/review',{method:'POST',body:JSON.stringify({user_id:currentUser.id,target_type:selectedReviewMedia.media_type,target_id:selectedReviewMedia.id,rating:reviewRating,review_text:text})}); renderReviews(); }
function reviewCard(r){ const lc=r.like_count??0; const cc=r.comment_count??0; const mine=r.user_id===currentUser.id; return `<article class="card" id="review-${r.id}"><div class="review-row"><img onclick="renderMediaDetail('${r.target_type}',${r.target_type==='movie'?r.movie_id:r.tv_show_id})" ${imageSrc(r.poster_path)}/><div><h2>${esc(r.title)}</h2><p class="muted">${esc(r.target_type)} · ${r.year} · ${r.rating}/5</p><p>${esc(r.review_text)}</p><div class="actions"><button id="review-like-${r.id}" class="pill ${r.liked_by_me?'active':''}" onclick="toggleReviewLike(${r.id})">♥ ${lc}</button><button id="review-comment-btn-${r.id}" class="pill" onclick="openReviewComments(${r.id})">💬 ${cc}</button><span class="pill">by ${esc(r.display_name)}</span></div>${mine?`<div class="review-owner-actions"><button class="secondary" onclick='openEditReview(${JSON.stringify(r).replaceAll("'","&apos;")})'>Edit</button><button class="danger pill" onclick="deleteReview(${r.id})">Delete</button></div>`:''}</div></div></article>`; }
function openEditReview(r){ modal(`<h2>Edit Review</h2><label>Rating</label><input id="edit_review_rating" type="number" min="0.5" max="5" step="0.5" value="${r.rating}"/><label>Review</label><textarea id="edit_review_text">${esc(r.review_text)}</textarea><button class="primary" onclick="saveEditedReview(${r.id})">Save Changes</button><button class="secondary" onclick="closeModal()">Cancel</button>`); }
async function saveEditedReview(id){ const rating=Number(edit_review_rating.value); const review_text=edit_review_text.value.trim(); if(!rating||!review_text)return alert('Please complete the review.'); await api(`/api/review/${id}`,{method:'PUT',body:JSON.stringify({user_id:currentUser.id,rating,review_text})}); closeModal(); renderReviews(); }
async function deleteReview(id){ if(!confirm('Delete this review?'))return; await api(`/api/review/${id}?user_id=${currentUser.id}`,{method:'DELETE'}); document.querySelector(`#review-${id}`)?.remove(); }
async function toggleReviewLike(id){ const d=await api(`/api/review/${id}/like`,{method:'POST',body:JSON.stringify({user_id:currentUser.id})}); const b=document.querySelector(`#review-like-${id}`); if(b){b.textContent=`♥ ${d.like_count}`; b.classList.toggle('active',d.liked);} }
async function openReviewComments(id){ const d=await api(`/api/review/${id}/comments`); modal(`<h2>Review Comments</h2>${d.comments.map(c=>`<div class="section"><strong>${esc(c.display_name)}:</strong> ${esc(c.comment_text)}</div>`).join('')||'<p class="muted">No comments yet.</p>'}<input id="review_comment_text" placeholder="Write a comment..."/><button class="primary" onclick="addReviewComment(${id})">Send</button><button class="secondary" onclick="closeModal()">Close</button>`); }
async function addReviewComment(id){ if(!review_comment_text.value.trim())return; const d=await api(`/api/review/${id}/comments`,{method:'POST',body:JSON.stringify({user_id:currentUser.id,comment_text:review_comment_text.value.trim()})}); const b=document.querySelector(`#review-comment-btn-${id}`); if(b)b.textContent=`💬 ${d.comment_count}`; closeModal(); }
async function renderMediaDetail(type,id,push=true){ currentPage=type==='movie'?'Movie':'TV Show'; if(push)pushHistory('Media',{type,id}); const d=await api(`/api/media/${type}/${id}`); const m=d.media; const year=type==='movie'?m.release_year:`${m.first_air_year||''}${m.last_air_year?' - '+m.last_air_year:''}`; appShell(`<article class="card"><div class="media-detail-hero"><img ${imageSrc(m.poster_path)}/><div><h2>${esc(m.title)}</h2><p class="muted">${year} · ${esc(m.genres||'')}</p><div class="media-rating">FILMO Rating: ${m.platform_rating||'No ratings yet'} / 5</div><p>${esc(m.overview||'')}</p>${type==='movie'?`<p><strong>Director:</strong> ${esc(m.director||'Not set')}</p>`:`<p><strong>Creator:</strong> ${esc(m.creator||'Not set')}</p>`}<p><strong>Cast:</strong> ${esc(m.cast||'Not set')}</p><p><strong>Country:</strong> ${esc(m.country||'')}</p><p><strong>Language:</strong> ${esc(m.language||'')}</p></div></div></article><article class="card"><h2>Reviews</h2>${d.reviews.length?d.reviews.map(r=>`<div class="section"><strong>${esc(r.display_name)}</strong><p class="muted">${r.rating}/5 · @${esc(r.username)}</p><p>${esc(r.review_text)}</p></div>`).join(''):'<p class="muted">No reviews for this title yet.</p>'}</article>`); }
if(currentUser){ const last=historyStack[historyIndex]; if(last)route(last,false); else navigate('Discover'); } else renderLogin();
