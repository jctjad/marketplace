// static/script.js

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
// Browse page – index.html
// ==============================
async function loadItems(query = "") {
  try {
    const url = query ? `/api/items?q=${encodeURIComponent(query)}` : "/api/items";
    const data = await fetchJSON(url);
    renderItemGrid(data.items || []);
  } catch (err) {
    console.error("Error loading items:", err);
  }
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

function initBrowsePage() {
  // Search input → call API with ?q=
  const searchInput = document.querySelector(".search input");
  if (searchInput) {
    searchInput.addEventListener("input", () => {
      const query = searchInput.value.trim().toLowerCase();
      loadItems(query);
    });
  }

  // Initial load
  loadItems();
}

// ==============================
// Item detail page – item.html
// ==============================
async function initItemPage() {
  // Item id from path: /item/<id>
  const parts = window.location.pathname.split("/");
  const id = parts[parts.length - 1];
  if (!id) return;

  try {
    const data = await fetchJSON(`/api/items/${id}`);
    const item = data.item;

    // Fill in fields
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
  } catch (err) {
    console.error("Error loading item:", err);
    const main = document.querySelector("main");
    if (main) {
      main.innerHTML = "<p>Sorry, this item could not be loaded.</p>";
    }
  }
}

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

  // keep your previewImage inline function from create_item.html if you like,
  // or move it here (but not strictly needed to prove REST separation)
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

// If you want, you can also preview avatar on file change (optional).
function bindEditAvatarPreview() {
  const input = document.querySelector('input[name="avatar"]');
  const preview = document.getElementById("edit-profile-avatar-preview");
  if (!input || !preview) return;

  input.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      preview.src = ev.target.result;
    };
    reader.readAsDataURL(file);
  });
}

// ==============================
// Bookmark toggle (kept from your old script)
// ==============================
function bindBookmarkIcons() {
  document.querySelectorAll(".item-card__bookmark").forEach((icon) => {
    icon.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      const current = icon.getAttribute("src");
      const alt = icon.dataset.altSrc;
      icon.setAttribute("src", alt);
      icon.dataset.altSrc = current;
    });
  });
}

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
    }
  }
});