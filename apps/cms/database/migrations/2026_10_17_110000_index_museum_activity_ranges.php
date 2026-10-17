<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

/** Bounded admin activity queries must not full-scan a growing private journal. */
return new class extends Migration {
    public function up(): void
    {
        Schema::table('museum_audit_records', static function (Blueprint $table): void {
            $table->index('created_at', 'museum_audit_created_at_idx');
            $table->index(['actor_id', 'created_at'], 'museum_audit_actor_date_idx');
        });
    }

    public function down(): void
    {
        Schema::table('museum_audit_records', static function (Blueprint $table): void {
            $table->dropIndex('museum_audit_actor_date_idx');
            $table->dropIndex('museum_audit_created_at_idx');
        });
    }
};
