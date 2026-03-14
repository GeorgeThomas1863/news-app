export const buildNewsForm = async (data) => {
  const mainContainer = document.createElement("div");
  mainContainer.id = "main-container";
  mainContainer.innerHTML = "";

  const navElement = await buildNavBar();
  const searchZone = await buildSearchZone();
  const bodySection = await buildBodySection(data);

  mainContainer.append(navElement, searchZone, bodySection);

  return mainContainer;
};

// Build navigation bar
export const buildNavBar = async () => {
  const nav = document.createElement("nav");
  nav.className = "navbar";

  const logo = document.createElement("div");
  logo.className = "nav-logo";
  logo.textContent = "Dispatch";

  const navCenter = document.createElement("div");
  navCenter.className = "nav-center";

  const navItems = [
    { text: "Feed", href: "/", active: true },
    { text: "Saved", href: "/saved", active: false },
    { text: "Digest", href: "/digest", active: false },
  ];

  for (let i = 0; i < navItems.length; i++) {
    const pill = document.createElement("a");
    pill.className = "nav-pill";
    pill.href = navItems[i].href;
    pill.textContent = navItems[i].text;
    if (navItems[i].active) pill.classList.add("active");
    navCenter.appendChild(pill);
  }

  const navRight = document.createElement("div");
  navRight.className = "nav-right";

  const avatar = document.createElement("div");
  avatar.className = "nav-avatar";
  avatar.textContent = "GK";

  navRight.appendChild(avatar);
  nav.append(logo, navCenter, navRight);

  return nav;
};

// Build search zone beneath nav
export const buildSearchZone = async () => {
  const searchZone = document.createElement("div");
  searchZone.className = "search-zone";

  const searchInput = document.createElement("input");
  searchInput.className = "search-input";
  searchInput.type = "text";
  searchInput.placeholder = "Search headlines, topics, sources...";

  searchZone.appendChild(searchInput);

  return searchZone;
};

// Build the main body section
export const buildBodySection = async (data) => {
  const body = document.createElement("div");
  body.className = "body-section";

  const topBlock = await buildTopNewsBlock(data.topNews);
  const categoriesSection = await buildCategoriesSection(data.categories);

  body.append(topBlock, categoriesSection);

  return body;
};

// Build the Top News accordion block
export const buildTopNewsBlock = async (topNews) => {
  const topBlock = document.createElement("div");
  topBlock.className = "top-block";

  const topHeader = await buildTopNewsHeader(topNews);
  const topStoriesList = await buildTopStoriesList(topNews);

  topBlock.append(topHeader, topStoriesList);

  return topBlock;
};

// Build the Top News header row
export const buildTopNewsHeader = async (topNews) => {
  const header = document.createElement("div");
  header.className = "top-header";
  header.setAttribute("data-label", "toggle-top-news");

  const leftSide = document.createElement("div");
  leftSide.className = "top-header-left";

  const badge = document.createElement("span");
  badge.className = "top-news-badge";
  badge.textContent = "Top News";

  const count = document.createElement("span");
  count.className = "top-news-count";
  count.textContent = `${topNews.length} stories`;

  leftSide.append(badge, count);

  const rightSide = document.createElement("div");
  rightSide.className = "top-header-right";

  const updated = document.createElement("span");
  updated.className = "top-news-updated";
  updated.textContent = "Updated 4m ago";

  const chev = document.createElement("span");
  chev.className = "top-news-chev";
  chev.setAttribute("data-label", "toggle-top-news");
  chev.textContent = "▲";

  rightSide.append(updated, chev);
  header.append(leftSide, rightSide);

  return header;
};

// Build the list of top news story rows
export const buildTopStoriesList = async (topNews) => {
  const list = document.createElement("div");
  list.className = "top-stories-list";
  list.id = "top-stories-list";

  for (let i = 0; i < topNews.length; i++) {
    const row = await buildTopStoryRow(topNews[i], i + 1);
    list.appendChild(row);
  }

  return list;
};

// Build a single top news story row
export const buildTopStoryRow = async (storyData, index) => {
  const row = document.createElement("div");
  row.className = "top-story-row";

  const num = document.createElement("div");
  num.className = "story-num";
  num.textContent = index;

  const textBlock = document.createElement("div");
  textBlock.className = "story-text";

  const headline = document.createElement("div");
  headline.className = "story-headline";
  headline.textContent = storyData.headline;

  const meta = document.createElement("div");
  meta.className = "story-meta";

  const source = document.createElement("span");
  source.className = "story-source";
  source.textContent = storyData.source;

  const dot = document.createElement("span");
  dot.textContent = "·";

  const time = document.createElement("span");
  time.textContent = storyData.time;

  meta.append(source, dot, time);
  textBlock.append(headline, meta);
  row.append(num, textBlock);

  return row;
};

// Build the categories section (label + 2 rows of 3)
export const buildCategoriesSection = async (categories) => {
  const section = document.createElement("div");
  section.className = "categories-section";

  const label = document.createElement("div");
  label.className = "categories-label";
  label.textContent = "Categories";

  const row1 = await buildCategoryRow(categories.slice(0, 3));
  const row2 = await buildCategoryRow(categories.slice(3, 6));

  section.append(label, row1, row2);

  return section;
};

// Build a row of 3 category accordions
export const buildCategoryRow = async (categoriesSlice) => {
  const row = document.createElement("div");
  row.className = "category-row";

  for (let i = 0; i < categoriesSlice.length; i++) {
    const card = await buildCategoryCard(categoriesSlice[i]);
    row.appendChild(card);
  }

  return row;
};

// Build a single category accordion card
export const buildCategoryCard = async (categoryData) => {
  const card = document.createElement("div");
  card.className = "category-card";
  card.setAttribute("data-category", categoryData.id);

  const head = await buildCategoryHead(categoryData);
  const body = await buildCategoryBody(categoryData);

  card.append(head, body);

  return card;
};

// Build the header row of a category card
export const buildCategoryHead = async (categoryData) => {
  const head = document.createElement("div");
  head.className = "category-head";
  head.setAttribute("data-label", "toggle-category");
  head.setAttribute("data-category", categoryData.id);

  const nameGroup = document.createElement("div");
  nameGroup.className = "category-name-group";

  const pip = document.createElement("span");
  pip.className = "category-pip";
  pip.style.background = categoryData.color;

  const name = document.createElement("span");
  name.className = "category-name";
  name.textContent = categoryData.name;

  const count = document.createElement("span");
  count.className = "category-count";
  count.textContent = categoryData.stories.length;

  nameGroup.append(pip, name, count);

  const chev = document.createElement("span");
  chev.className = "category-chev";
  chev.setAttribute("data-label", "toggle-category");
  chev.textContent = categoryData.expanded ? "▲" : "▼";

  head.append(nameGroup, chev);

  return head;
};

// Build the collapsible body of a category card
export const buildCategoryBody = async (categoryData) => {
  const body = document.createElement("div");
  body.className = "category-body";
  body.id = `category-body-${categoryData.id}`;

  if (!categoryData.expanded) {
    body.style.display = "none";
  }

  for (let i = 0; i < categoryData.stories.length; i++) {
    const item = await buildCategoryStoryItem(categoryData.stories[i]);
    body.appendChild(item);
  }

  return body;
};

// Build a single story item inside a category body
export const buildCategoryStoryItem = async (storyData) => {
  const item = document.createElement("div");
  item.className = "category-story-item";

  const headline = document.createElement("div");
  headline.className = "cat-story-headline";
  headline.textContent = storyData.headline;

  const meta = document.createElement("div");
  meta.className = "cat-story-meta";
  meta.textContent = `${storyData.source} · ${storyData.time}`;

  item.append(headline, meta);

  return item;
};
