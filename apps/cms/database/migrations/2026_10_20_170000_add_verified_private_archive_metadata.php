<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::table('museum_publication_runs', static function (Blueprint $table): void {
            $table->string('archive_id', 160)->nullable();
            $table->char('archive_receipt_sha256', 64)->nullable();
            $table->unsignedInteger('archive_file_count')->nullable();
            $table->timestampTz('archived_at')->nullable();
        });
    }

    public function down(): void
    {
        Schema::table('museum_publication_runs', static function (Blueprint $table): void {
            $table->dropColumn(['archive_id','archive_receipt_sha256','archive_file_count','archived_at']);
        });
    }
};
