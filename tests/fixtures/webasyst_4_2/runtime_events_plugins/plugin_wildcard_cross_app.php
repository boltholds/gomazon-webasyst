<?php
// FIXTURE_KIND: source-reduced
// SOURCE_COMMIT: 39c267a2fabfb0cd6d94f4dd86b23b4750328dd5
// SOURCE_PATH: wa-apps/site/plugins/rublesign/lib/config/plugin.php
return array(
    'name' => 'Символ рубля',
    'img' => 'img/rublesign.png',
    'version' => '1.0.0',
    'vendor' => 'webasyst',
    'site_settings' => true,
    'handlers' => array(
        '*' => array(
            array(
                'event_app_id' => 'webasyst',
                'event' => 'backend_header',
                'class' => 'siteRublesignPlugin',
                'method' => 'backendHeader',
            ),
            array(
                'event_app_id' => 'shop',
                'event' => 'frontend_head',
                'class' => 'siteRublesignPlugin',
                'method' => 'frontendHead',
            ),
            array(
                'event_app_id' => 'site',
                'event' => 'frontend_page',
                'class' => 'siteRublesignPlugin',
                'method' => 'frontendPage',
            ),
        ),
    ),
);
