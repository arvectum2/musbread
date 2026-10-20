<?php

declare(strict_types=1);

use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;

/**
 * MoonShine's original migration inserts explicit Admin id=1, which does
 * not advance PostgreSQL IDENTITY/serial sequences. Before a new role uses
 * the default nextval(), align its sequence to the highest persisted ID.
 * MySQL and SQLite are already safe with an explicit initial ID.
 */
return new class extends Migration {
    public function up(): void
    {
        if (DB::getDriverName() !== 'pgsql') return;

        // Fixed local table/column literals, not user-controlled SQL identifiers.
        // Keep the role rows and their foreign keys untouched.
        DB::statement("SELECT setval(
            pg_get_serial_sequence('moonshine_user_roles', 'id'),
            GREATEST((SELECT COALESCE(MAX(id), 1) FROM moonshine_user_roles), 1),
            true
        )");
    }

    public function down(): void
    {
        // Restoring the old sequence would invite primary-key collisions.
    }
};
