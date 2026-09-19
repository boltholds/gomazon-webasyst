<?php
// FIXTURE_KIND: source-reduced
// SOURCE_COMMIT: 39c267a2fabfb0cd6d94f4dd86b23b4750328dd5
// SOURCE_PATH: wa-apps/blog/plugins/myposts/lib/config/plugin.php
return array(
    'name' => 'My posts',
    'description' => 'Backend filtering for self-authored posts',
    'img' => '/img/myposts.png',
    'vendor' => 'webasyst',
    'version' => '1.2.0',
    'handlers' => array(
        'search_posts_backend' => 'postSearch',
        'backend_sidebar' => 'backendSidebar',
    ),
);
