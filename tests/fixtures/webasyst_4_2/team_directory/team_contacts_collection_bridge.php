<?php
// SOURCE_COMMIT: 39c267a2fabfb0cd6d94f4dd86b23b4750328dd5
// SOURCE_PATH: wa-apps/team/lib/handlers/contacts.contacts_collection.handler.php
class teamContactsContacts_collectionHandler extends waEventHandler
{
    public function execute(&$params)
    {
        return !!wa('team')->event('contacts_collection', $params);
    }
}
