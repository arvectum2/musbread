<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::create('museum_editorial_review_notes', static function (Blueprint $table): void {
            $table->id();
            $table->string('baseline_sha256', 64);
            $table->string('candidate_sha256', 64);
            $table->string('item_group', 16);
            $table->string('item_key', 200);
            $table->string('decision', 20);
            $table->text('note');
            $table->unsignedBigInteger('actor_id');
            $table->timestamp('created_at')->useCurrent();
            $table->index(['baseline_sha256', 'candidate_sha256', 'item_group'], 'museum_review_snapshot_idx');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('museum_editorial_review_notes');
    }
};
