// Flyout Menu Functions
var toggles = {
  ".search-toggle": "#search-input",
  ".lang-toggle": "#lang-menu",
  ".share-toggle": "#share-menu",
  ".nav-toggle": "#site-nav-menu"
};

$.each(toggles, function(toggle, menu) {
  $(toggle).on("click", function() {
    if ($(menu).hasClass("active")) {
      $(".menu").removeClass("active");
      $("#wrapper").removeClass("overlay");
    } else {
      $("#wrapper").addClass("overlay");
      $(".menu").not($(menu + ".menu")).removeClass("active");
      $(menu).addClass("active");
      if (menu == "#search-input") {$("#search-results").toggleClass("active");}
    }
  });
});

// Click anywhere outside a flyout to close
$(document).on("click", function(e) {
  if ($(e.target).is(".lang-toggle, .lang-toggle span, #lang-menu, .share-toggle, .share-toggle i, #share-menu, .search-toggle, .search-toggle i, #search-input, #search-results .mini-post, .nav-toggle, .nav-toggle i, #site-nav") === false) {
    $(".menu").removeClass("active");
    $("#wrapper").removeClass('overlay');
  }
});

// Check to see if the window is top if not then display button
$(window).scroll(function() {
  if ($(this).scrollTop()) {
    $('#back-to-top').fadeIn();
  } else {
    $('#back-to-top').fadeOut();
  }
});

// Click event to scroll to top
$('#back-to-top').click(function() {
  $('html, body').animate({scrollTop: 0}, 1000);
  return false;
});

// Search
var idx = null;         // Lunr index
var resultDetails = []; // Will hold the data for the search results (titles and summaries)
var $searchResults;     // The element on the page holding search results
var $searchInput;       // The search box element
var searchIndexState = 'idle'; // idle | loading | ready | error
var searchMessages = {
  noResults: {{ i18n "search_no_results" | default "No results found." | jsonify }},
  error: {{ i18n "search_error" | default "Could not load the search index." | jsonify }}
};

// Ignore accents, so "mon" finds "món" and "cami" finds "camí". It runs before
// the trimmer, which would otherwise strip accented letters from word edges.
var foldDiacritics = function (token) {
  return token.update(function (str) {
    return str.normalize ? str.normalize('NFD').replace(/[̀-ͯ]/g, '') : str;
  });
};
lunr.Pipeline.registerFunction(foldDiacritics, 'foldDiacritics');

// Also split words on apostrophes, so "l'aigua" can be found as "aigua".
lunr.tokenizer.separator = /[\s\-'’]+/;

function searchMessage(text) {
  $searchResults.innerHTML = '<article class="mini-post"><main><p>' + text + '</p></main></article>';
}

// The index (index.json, built by Hugo) is only requested the first time the
// search is opened, not on every page load.
function loadSearchIndex() {
  if (searchIndexState != 'idle') { return; }
  searchIndexState = 'loading';

  var request = new XMLHttpRequest();
  var lang = document.documentElement.lang;
  var pathArgs = ["{{ replaceRE "/$" "" .BaseURL }}", "index.json"];
  if (lang != "{{ .Language.Lang }}") {
    pathArgs.splice(1, 0, lang);
  }
  var path = pathArgs.join("/");

  request.open("GET", path, true);
  request.onload = function() {
    if (request.status >= 200 && request.status < 400) {
      var documents = JSON.parse(request.responseText);

      // Build the index so Lunr can search it. The `ref` field holds the URL
      // of the page; title, description and body are the fields searched.
      idx = lunr(function () {
        this.pipeline.before(lunr.trimmer, foldDiacritics);
        this.searchPipeline.before(lunr.stemmer, foldDiacritics);

        this.ref('ref');
        this.field('title');
        this.field('description');
        this.field('body');

        documents.forEach(function(doc) {
            this.add(doc);
            resultDetails[doc.ref] = {
              'title': doc.title,
              'date': doc.date,
              'description': doc.description,
            };
        }, this);
      });
      searchIndexState = 'ready';
      // Run the search for whatever was typed while the index was loading
      runSearch();
    } else {
      searchIndexState = 'error';
      searchMessage(searchMessages.error);
    }
  };
  request.onerror = function() {
    searchIndexState = 'error';
    searchMessage(searchMessages.error);
  };
  request.send();
}

function runSearch() {
  var query = $searchInput.value.replace(/^\s+|\s+$/g, '');
  if (query == '') {
    $searchResults.innerHTML = '';
    return;
  }
  if (searchIndexState == 'error') {
    searchMessage(searchMessages.error);
    return;
  }
  if (searchIndexState != 'ready') {
    loadSearchIndex();
    return;
  }
  renderSearchResults(search(query));
}

window.addEventListener('load', function () {
  $searchResults = document.getElementById('search-results');
  $searchInput   = document.getElementById('search-input');
  if (!$searchResults || !$searchInput) { return; }

  $searchInput.addEventListener('focus', loadSearchIndex);
  $searchInput.addEventListener('input', runSearch);
  var toggles = document.querySelectorAll('.search-toggle');
  for (var i = 0; i < toggles.length; i++) {
    toggles[i].addEventListener('click', loadSearchIndex);
  }
});

function renderSearchResults(results) {
  if (results.length == 0) {
    searchMessage(searchMessages.noResults);
    return;
  }
  var html = '';
  results.forEach(function(result) {
    var details = resultDetails[result.ref];
    html += '<article class="mini-post"><a href="' + result.ref + '"><header><h2>' + details.title + '</h2><time class="published" datetime="">' + details.date + '</time></header><main><p>' + details.description + '</p></main></a></article>';
  });
  $searchResults.innerHTML = html;
}

function search(query) {
  try {
    return idx.search(query);
  } catch (e) {
    // Lunr throws on malformed queries (for example a lone "+" or ":")
    return [];
  }
}
