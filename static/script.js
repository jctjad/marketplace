// static/script.js

// ==============================
// Global Variables (tracks items being displayed)
// ==============================
let allItems = [];
let currentFilter = "all"; // "all" or "bookmarks" (will extend to items being sold too)
let currentUserId = null;

// ==============================
// Helper: detect page
// ==============================
function getPageType() {
  const body = document.body;
  return body ? body.dataset.page : null;
}

// ==============================
// REST helpers
// ==============================
async function fetchJSON(url, options = {}) {
  const resp = await fetch(url, options);
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`HTTP ${resp.status}: ${text}`);
  }
  return resp.json();
}

// ==============================
// Browse page – index.html (load current user from backend)
// ==============================
async function loadCurrentUser() {
  try {
    const res = await fetch("/api/profile/me");
    const data = await res.json();
    currentUserId = data.user.id;
    console.log("Current user ID:", currentUserId);
  } catch (err) {
    console.error("Failed to load current user:", err);
  }
}

// ==============================
// Browse page – index.html (load items from backend)
// ==============================
async function loadItems(query = "") {
  try {
    const params = query ? `?q=${encodeURIComponent(query)}` : "";
    const res = await fetch(`/api/items${params}`);

    if (!res.ok) {
      console.error("Failed to load items", await res.text());
      return;
    }

    const data = await res.json();

    allItems = data.items || [];
    applyFilterAndRender();
  } catch (err) {
    console.error("Error loading items:", err);
  }
}

// Apply currentFilter, then render
function applyFilterAndRender() {
  let itemsToShow = allItems;

  if (currentFilter === "bookmarks") {
    itemsToShow = allItems.filter((item) => item.bookmarked);
  } else if (currentFilter === "selling-items") {
    itemsToShow = allItems.filter(item => item.seller_id === currentUserId);
  }

  renderItemGrid(itemsToShow);
}

function renderItemGrid(items) {
  const grid = document.querySelector(".grid");
  if (!grid) return;

  grid.innerHTML = ""; // clear old cards

  if (!items.length) {
    const p = document.createElement("p");
    p.className = "empty-msg";
    p.textContent = "No items yet — be the first to list something!";
    grid.appendChild(p);
    return;
  }

  items.forEach((item) => {
    const a = document.createElement("a");
    a.className = "card";
    a.href = `/item/${item.id}`;

    const imgThumb = document.createElement("img");
    imgThumb.className = "item-card__thumb";
    imgThumb.src = item.item_photos || "/static/assets/item_placeholder.svg";
    imgThumb.alt = item.name || "Item";

    const bookmark = document.createElement("img");
    bookmark.className = "item-card__bookmark";
    bookmark.src = "/static/assets/bookmark.svg";
    bookmark.dataset.altSrc = "/static/assets/bookmark-filled.svg";
    bookmark.dataset.itemId = item.id;
    bookmark.dataset.bookmarked = item.bookmarked ? "true" : "false";
     if (item.bookmarked) { // show as filled if already bookmarked
      bookmark.src = "/static/assets/bookmark-filled.svg";
      bookmark.dataset.altSrc = "/static/assets/bookmark.svg";
    } else {  // default unfilled
      bookmark.src = "/static/assets/bookmark.svg";
      bookmark.dataset.altSrc = "/static/assets/bookmark-filled.svg";
    }
    bookmark.alt = "Bookmark";

    const body = document.createElement("div");
    body.className = "item-card__body";

    const top = document.createElement("div");
    top.className = "item-card__top";

    const title = document.createElement("div");
    title.className = "item-card__title";
    title.textContent = item.name || "";

    const price = document.createElement("div");
    price.className = "item-card__price";
    const p = Number(item.price || 0).toFixed(2);
    price.textContent = `$${p}`;

    top.appendChild(title);
    top.appendChild(price);

    const bottom = document.createElement("div");
    bottom.className = "item-card__bottom";

    const seller = document.createElement("div");
    seller.className = "item-card__seller";
    if (item.seller) {
      seller.textContent = item.seller.first_name || "Seller";
    } else {
      seller.textContent = "Unknown Seller";
    }

    const paymentIcons = document.createElement("div");
    paymentIcons.className = "item-card__payment-icons";

    (item.payment_options || []).forEach((method) => {
      let iconSrc = null;
      if (method.includes("Venmo")) iconSrc = "/static/assets/venmo.svg";
      else if (method.includes("Zelle")) iconSrc = "/static/assets/zelle.svg";
      else if (method.includes("Cash")) iconSrc = "/static/assets/cash.svg";

      if (iconSrc) {
        const icon = document.createElement("img");
        icon.className = "icon";
        icon.src = iconSrc;
        icon.alt = method;
        paymentIcons.appendChild(icon);
      }
    });

    bottom.appendChild(seller);
    bottom.appendChild(paymentIcons);

    body.appendChild(top);
    body.appendChild(bottom);

    a.appendChild(imgThumb);
    a.appendChild(bookmark);
    a.appendChild(body);

    grid.appendChild(a);
  });

  // Rebind bookmark toggle handlers
  bindBookmarkIcons();
}

// NEW: this was missing – it wires up search + initial fetch
function initBrowsePage() {
  const searchInput = document.querySelector(".search input");
  if (searchInput) {
    searchInput.addEventListener("input", () => {
      const query = searchInput.value.trim();
      loadItems(query);
    });
  }

  // Initial load
  loadCurrentUser();
  loadItems();
}

// ==============================
// Item detail page – item.html
// ==============================
async function initItemPage() {
  const parts = window.location.pathname.split("/");
  const id = parts[parts.length - 1];
  if (!id) return;

  try {
    const data = await fetchJSON(`/api/items/${id}`);
    const item = data.item;

    // Fill UI fields
    const titleEl = document.querySelector("#item-name");
    const priceEl = document.querySelector("#item-price");
    const imgEl = document.querySelector("#item-image");
    const conditionEl = document.querySelector("#item-condition");
    const sellerEl = document.querySelector("#seller-name");
    const paymentContainer = document.querySelector("#payment-options");
    const descEl = document.querySelector("#item-description");

    if (titleEl) titleEl.textContent = item.name || "";
    if (priceEl) priceEl.textContent = `$${Number(item.price || 0).toFixed(2)}`;
    if (imgEl) {
      imgEl.src = item.item_photos || "/static/assets/item_placeholder.svg";
      imgEl.alt = item.name || "Item image";
    }
    if (conditionEl) conditionEl.textContent = item.condition || "—";
    if (sellerEl && item.seller) {
      sellerEl.textContent = `${item.seller.first_name || ""} ${item.seller.last_name || ""}`.trim();
    }
    if (descEl) descEl.textContent = item.description || "";

    // Payment options
    if (paymentContainer) {
      paymentContainer.innerHTML = "";
      (item.payment_options || []).forEach((option) => {
        const div = document.createElement("div");
        div.className = "payment-option";

        let iconSrc = null;
        if (option === "Cash") iconSrc = "/static/assets/cash.svg";
        if (option === "Venmo") iconSrc = "/static/assets/venmo.svg";
        if (option === "Zelle") iconSrc = "/static/assets/zelle.svg";

        if (iconSrc) {
          const img = document.createElement("img");
          img.src = iconSrc;
          img.alt = option;
          img.className = "icon";
          div.appendChild(img);
        }

        const span = document.createElement("span");
        span.textContent = option;
        div.appendChild(span);

        paymentContainer.appendChild(div);
      });
    }

    if (item.is_owner) {
      const actions = document.getElementById("owner-actions");
      if (actions) actions.style.display = "block";

      const editBtn = document.getElementById("edit-item-btn");
      if (editBtn) editBtn.href = `/item/${item.id}/edit`;

      const delBtn = document.getElementById("delete-item-btn");

      // MODAL DELETE
      const modal = document.getElementById("deleteModal");
      const confirmBtn = document.getElementById("confirmDelete");
      const cancelBtn = document.getElementById("cancelDelete");

      delBtn.addEventListener("click", () => {
        modal.classList.remove("hidden");
      });

      cancelBtn.addEventListener("click", () => {
        modal.classList.add("hidden");
      });

      confirmBtn.addEventListener("click", async () => {
        try {
          const resp = await fetch(`/api/items/${item.id}`, {
            method: "DELETE"
          });
          if (!resp.ok) throw new Error(await resp.text());
          window.location.href = "/";
        } catch (err) {
          console.error("Delete failed:", err);
          alert("There was an error deleting the item.");
        }
      });
    }
  } catch (err) {
    console.error("Error loading item:", err);
    const main = document.querySelector("main");
    if (main) {
      main.innerHTML = "<p>Sorry, this item could not be loaded.</p>";
    }
  }
} // ← IMPORTANT: closes initItemPage()


// ==============================
// Create item page – create_item.html
// ==============================
function initCreateItemPage() {
  const form = document.getElementById("createForm");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const formData = new FormData(form);

    try {
      const resp = await fetch("/api/items", {
        method: "POST",
        body: formData,
      });
      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(text || resp.statusText);
      }
      const data = await resp.json();
      const itemId = data.item && data.item.id;
      if (itemId) {
        window.location.href = `/item/${itemId}`;
      } else {
        alert("Item created but response was missing ID.");
      }
    } catch (err) {
      console.error("Error creating item:", err);
      alert("There was an error creating the item.");
    }
  });

  // (Optional) keep separate inline preview function in create_item.html if you like.
}

// ==============================
// Edit item page – edit_item.html
// ==============================
async function initEditItemPage() {
  // Extract item id from URL: /item/<id>/edit
  const parts = window.location.pathname.split("/");
  const id = parts[parts.length - 2]; 
  if (!id) return;

  // Get form fields
  const form = document.getElementById("editForm");
  if (!form) return;

  const nameInput = form.querySelector('input[name="name"]');
  const descInput = form.querySelector('textarea[name="description"]');
  const priceInput = form.querySelector('input[name="price"]');
  const conditionSelect = form.querySelector('select[name="condition"]');
  const paymentCheckboxes = form.querySelectorAll('input[name="payment_options"]');
  const fileInput = form.querySelectorAll('input[name="image_file"]');

  // 1. Load existing data
  try {
    const data = await fetchJSON(`/api/items/${id}`);
    const item = data.item;

    // Pre-fill fields
    if (nameInput) nameInput.value = item.name || "";
    if (descInput) descInput.value = item.description || "";
    if (priceInput) priceInput.value = item.price || "";
    if (conditionSelect) conditionSelect.value = item.condition || "New";

    paymentCheckboxes.forEach(cb => {
      cb.checked = item.payment_options.includes(cb.value);
    });

    // Load current image preview if you want (optional)
    const imgPreview = document.getElementById("edit-image-preview");
    if (imgPreview) {
      imgPreview.src = item.item_photos || "/static/assets/item_placeholder.svg";
    }

  } catch (err) {
    console.error("Failed to load item for editing:", err);
  }

  // 2. Handle Save Changes
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    
    // Checking to see if the user uploaded a new file
    if (fileInput.files[0]) {
      uploaded_photo = fileInput.files[0];
      console.log(uploaded_photo);
    }

    // Collect updated fields
    const updatedData = {
      name: nameInput.value.trim(),
      description: descInput.value.trim(),
      item_photos: uploaded_photo,
      price: priceInput.value.trim(),
      condition: conditionSelect.value,
      payment_options: Array.from(paymentCheckboxes)
        .filter(cb => cb.checked)
        .map(cb => cb.value)
    };

    try {
      const resp = await fetch(`/api/items/${id}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(updatedData)
      });

      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(text);
      }

      // Redirect back to item page
      window.location.href = `/item/${id}`;
    } catch (err) {
      console.error("Update error:", err);
      alert("There was an error saving your changes.");
    }
  });
}

// ==============================
// Profile pages – profile.html, edit_profile.html
// ==============================
async function loadProfileData() {
  try {
    const data = await fetchJSON("/api/profile/me");
    const user = data.user;

    // Profile view
    const nameEl = document.getElementById("profile-name");
    const bioEl = document.getElementById("profile-bio");
    const avatarEl = document.getElementById("profile-avatar");

    if (nameEl) {
      nameEl.textContent = `${user.first_name || ""} ${user.last_name || ""}`.trim() || "User";
    }
    if (bioEl) {
      bioEl.textContent = user.profile_description || "No bio yet. Click “Edit profile” to add a public bio.";
    }
    if (avatarEl) {
      avatarEl.src = user.profile_image || "/static/assets/avatar.svg";
    }

    // Edit profile page (pre-fill)
    const editBio = document.getElementById("edit-profile-bio");
    const editAvatarPreview = document.getElementById("edit-profile-avatar-preview");

    if (editBio) {
      editBio.value = user.profile_description || "";
    }
    if (editAvatarPreview) {
      editAvatarPreview.src = user.profile_image || "/static/assets/avatar.svg";
    }
  } catch (err) {
    console.error("Error loading profile:", err);
  }
}

// ==============================
// Edit profile avatar logic
// ==============================

// Global blob for cropped avatar
let avatarCroppedBlob = null;

// Crop an image object to a centered square on a canvas
function cropImageToSquare(image) {
  const size = Math.min(image.naturalWidth, image.naturalHeight);
  const sx = (image.naturalWidth - size) / 2;
  const sy = (image.naturalHeight - size) / 2;

  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(image, sx, sy, size, size, 0, 0, size, size);
  return canvas;
}

// Preview + crop avatar client-side
function bindEditAvatarPreview() {
  const input = document.getElementById("avatar-input");
  const preview = document.getElementById("edit-profile-avatar-preview");
  if (!input || !preview) return;

  input.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      alert("Please select an image file.");
      return;
    }

    const reader = new FileReader();
    reader.onload = (ev) => {
      const img = new Image();
      img.onload = () => {
        const canvas = cropImageToSquare(img);
        canvas.toBlob(
          (blob) => {
            if (!blob) return;
            avatarCroppedBlob = blob;
            const url = URL.createObjectURL(blob);
            preview.src = url;
          },
          "image/jpeg",
          0.9
        );
      };
      img.src = ev.target.result;
    };
    reader.readAsDataURL(file);
  });
}

// Click overlay → open file picker
function bindAvatarOverlayClick() {
  const overlay = document.querySelector(".avatar-overlay");
  const input = document.getElementById("avatar-input");
  if (!overlay || !input) return;

  overlay.addEventListener("click", () => {
    input.click();
  });
}

// Intercept form submit to send cropped blob
function bindEditProfileFormSubmit() {
  const form = document.getElementById("edit-profile-form");
  const input = document.getElementById("avatar-input");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    // If user didn't pick a new avatar, let the normal form submit happen
    if (!input || !input.files || !input.files.length || !avatarCroppedBlob) {
      return;
    }

    e.preventDefault();

    const formData = new FormData(form);
    // Replace original avatar file with cropped one
    formData.delete("avatar");
    const croppedFile = new File([avatarCroppedBlob], "avatar.jpg", {
      type: "image/jpeg",
    });
    formData.append("avatar", croppedFile);

    try {
      const resp = await fetch(form.action, {
        method: "POST",
        body: formData,
      });

      if (resp.redirected) {
        window.location.href = resp.url;
      } else {
        // Fallback: reload page
        window.location.reload();
      }
    } catch (err) {
      console.error("Error saving profile:", err);
      alert("There was an error saving your profile.");
    }
  });
}

// ==============================
// Category dropdown button
// ==============================
(function () {
  const btn = document.getElementById('categoryFilter');
  const menu = document.getElementById('categoryMenu');
  if (!btn || !menu) return;

  const closeMenu = () => {
    btn.setAttribute('aria-expanded', 'false');
  };

  btn.addEventListener('click', (e) => {
    const expanded = btn.getAttribute('aria-expanded') === 'true';
    btn.setAttribute('aria-expanded', String(!expanded));
  });

  menu.addEventListener('click', (e) => {
    const target = e.target.closest('button[data-value]');
    if (!target) return;
    const label = target.textContent.trim();
    btn.innerHTML = `${label} ▾`;
    closeMenu();
  });

  // Close popup
  document.addEventListener('click', (e) => {
    if (e.target === btn || menu.contains(e.target)) return;
    closeMenu();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeMenu();
  });
})();

// ==============================
// Hook up filter dropdown to change the items being displayed
// ==============================
const categoryFilterBtn = document.getElementById("categoryFilter");
const categoryMenu = document.getElementById("categoryMenu");

if (categoryMenu && categoryFilterBtn) {
  categoryMenu.querySelectorAll("button[data-value]").forEach(btn => {
    btn.addEventListener("click", () => {
      const value = btn.dataset.value; // "all" or "bookmarks" or "selling-items"
      currentFilter = value;

      if (value === "bookmarks") {
        categoryFilterBtn.textContent = "Bookmarks ▾";
      } else if (value === "selling-items") {
        categoryFilterBtn.textContent = "Your Items ▾";
      } else {
        categoryFilterBtn.textContent = "All Items ▾";
      }

      applyFilterAndRender();
    });
  });
}

// ==============================
// Handles bookmark icon switch with REST
// ==============================
function bindBookmarkIcons() {
  document.querySelectorAll(".item-card__bookmark").forEach((icon) => {
    icon.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();

      // 1. Swap the icon image
      const current = icon.getAttribute("src");
      const alt = icon.dataset.altSrc;
      icon.setAttribute("src", alt);
      icon.dataset.altSrc = current;

      // 2. Toggle bookmark state in a data attribute
      const wasBookmarked = icon.dataset.bookmarked === "true";
      const isNowBookmarked = !wasBookmarked;
      icon.dataset.bookmarked = isNowBookmarked ? "true" : "false";

      // 3. Update local JS state (allItems) so it stays in sync with UI
      const itemId = icon.dataset.itemId;
      const itemIdNum = Number(itemId);
      const itemObj = allItems.find((i) => i.id === itemIdNum);

      if (itemObj) {
        itemObj.bookmarked = isNowBookmarked;
      }

      // 4. Re-apply the filter so it disappears from the grid.
      if (currentFilter === "bookmarks" && !isNowBookmarked) {
        applyFilterAndRender();
        return;
      }

      // 5. Send REST request to backend
      updateBookmarkOnServer(itemId, isNowBookmarked);
    });
  });
}

// ==============================
// Updates bookmark_items field in user table
// ==============================
async function updateBookmarkOnServer(itemId, isBookmarked) {
  try {
    const response = await fetch("/api/bookmark", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
      },
      credentials: "include", // send cookies/session
      body: JSON.stringify({
        item_id: itemId,
        bookmarked: isBookmarked,
      }),
    });

    if (!response.ok) {
      console.error("Failed to update bookmark", await response.text());
    }
  } catch (err) {
    console.error("Error updating bookmark", err);
  }
}

// ==============================
// Messaging 
// ==============================
let socket;

// Open chat box
async function openForm(){
  const chat_form = document.getElementById("chatForm");
  const chat_screen = document.getElementById("messages");
  chat_form.style.display = "block";
  chat_screen.style.display = "grid";
  // Item id from path: /item/<id>
  const parts = window.location.pathname.split("/");
  const id = parts[parts.length - 1];
  
  const data_user = await fetchJSON("/api/profile/me");
  const user = data_user.user;

  const data_item = await fetchJSON(`/api/items/${id}`);
  const item = data_item.item; 
  
  socket = io();
  socket.emit("join", item, user);
  socket.on("message", function(data) {
    var messages = document.getElementById('messages');
    messages.innerHTML += `<span>${data}</span>`;
  });

  chat_form.addEventListener("submit", async (e) => {
    e.preventDefault();
    
    // var message_to_add;
    
    // const msg_info = { user_data:user, item_data:item, message:message_to_add};

    // const resp = await fetch("api/messages", {
    //   method: "POST",
    //   headers: {
    //     'Content-Type': 'application/json'
    //   },
    //   body: JSON.stringify(msg_info)
    // });
    // const data = await resp.json();

  });
}

// Close chat box
async function closeForm(){
  document.getElementById("chatForm").style.display = "none";
  const data_user = await fetchJSON("/api/profile/me");
  const user = data_user.user;
}

// Function to send messages
async function sendMessage(){
  const data = await fetchJSON("/api/profile/me");
  const user = data.user;

  var msgInput = document.getElementById("msg");
  var message = msgInput.value;


  socket.send(message, user);
  msgInput.value = "";
}

/* USER PROFILE */
// ==============================
// Misc: year stamp
// ==============================
function updateYear() {
  document.querySelectorAll("#year").forEach((n) => {
    n.textContent = new Date().getFullYear();
  });
}

// ==============================
// Entry point
// ==============================
document.addEventListener("DOMContentLoaded", () => {
  updateYear();

  const page = getPageType();
  if (page === "browse") {
    initBrowsePage();
  } else if (page === "item") {
    initItemPage();
  } else if (page === "create-item") {
    initCreateItemPage();
  } else if (page === "profile" || page === "edit-profile") {
    loadProfileData();
    if (page === "edit-profile") {
      bindEditAvatarPreview();
      bindAvatarOverlayClick();
      bindEditProfileFormSubmit();
    }
  } else if (page === "edit-item") {
  initEditItemPage();
  }
});
