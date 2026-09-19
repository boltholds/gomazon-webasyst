<?php
/*
SOURCE_SNAPSHOT: Webasyst Framework 4.2.0
SOURCE_COMMIT: 39c267a2fabfb0cd6d94f4dd86b23b4750328dd5
SOURCE_PATH: wa-system/webasyst/lib/config/app.php
FIXTURE_KIND: source-reduced
*/

return array(
    'name'         => 'Webasyst',
    'prefix'       => 'webasyst',
    'version'      => '4.2.0',
    'critical'     => '4.2.0',
    'vendor'       => 'webasyst',
    'csrf'         => true,
    'header_items' => array(
        'settings' => array(
            'icon'   => 'img/wa-settings/settings.svg',
            'name'   => 'Settings',
            'link'   => 'settings',
            'rights' => 'backend',
        ),
    ),
    'ui' => '2.0',
);
