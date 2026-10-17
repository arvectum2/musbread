<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::create('museum_content_approvals', static function (Blueprint $table): void {
            $table->id();
            // Preserve an audit reference even if the editor deletes the content record.
            $table->unsignedBigInteger('museum_entry_id')->index();
            $table->unsignedBigInteger('actor_id');
            $table->char('revision_sha256', 64);
            // Actual DB-recorded UTC approval time, never inferred from published_at.
            $table->timestampTz('approved_at');
            $table->string('dispatch_status', 20)->default('pending');
            $table->unsignedBigInteger('publication_run_id')->nullable();
            $table->timestamps();
            $table->unique(['museum_entry_id', 'revision_sha256'], 'museum_approval_revision_unique');
            $table->index(['approved_at', 'dispatch_status'], 'museum_approval_status_time');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('museum_content_approvals');
    }
};
