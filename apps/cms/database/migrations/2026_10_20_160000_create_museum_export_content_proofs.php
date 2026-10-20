<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::table('museum_publication_runs', static function (Blueprint $table): void {
            $table->timestampTz('content_verified_at')->nullable();
            $table->unsignedInteger('content_proof_count')->nullable();
            $table->char('manifest_sha256', 64)->nullable();
        });
        Schema::create('museum_export_content_proofs', static function (Blueprint $table): void {
            $table->id();
            $table->unsignedBigInteger('publication_run_id')->index();
            $table->unsignedBigInteger('approval_id');
            $table->string('subject_kind', 16);
            $table->unsignedBigInteger('subject_id');
            $table->char('revision_sha256', 64);
            $table->char('snapshot_sha256', 64);
            $table->char('export_record_sha256', 64);
            $table->unique(['publication_run_id', 'subject_kind', 'subject_id'], 'museum_export_proof_subject_unique');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('museum_export_content_proofs');
        Schema::table('museum_publication_runs', static function (Blueprint $table): void {
            $table->dropColumn(['content_verified_at','content_proof_count','manifest_sha256']);
        });
    }
};
