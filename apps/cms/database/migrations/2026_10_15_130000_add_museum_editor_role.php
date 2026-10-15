<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;

return new class extends Migration {
    public function up(): void
    {
        if (! DB::table('moonshine_user_roles')->where('name', 'Editor')->exists()) {
            DB::table('moonshine_user_roles')->insert([
                'name' => 'Editor', 'created_at' => now(), 'updated_at' => now(),
            ]);
        }
    }

    public function down(): void
    {
        // Do not silently remove the role once assigned to a real editor.
        if (! DB::table('moonshine_users')
            ->whereIn('moonshine_user_role_id', DB::table('moonshine_user_roles')->where('name', 'Editor')->select('id'))
            ->exists()) {
            DB::table('moonshine_user_roles')->where('name', 'Editor')->delete();
        }
    }
};
