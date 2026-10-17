<?php
use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;
return new class extends Migration {
    public function up(): void {
        Schema::create('museum_visitor_contacts', static function(Blueprint $table):void {
            $table->id();
            $table->string('scope',20)->unique()->default('primary');
            foreach (['address','metro','phone','phone_href','email','opening_hours',
                'admission_hours','closed_day','sanitary_day'] as $field) $table->string($field,255)->nullable();
            $table->string('status',16)->default('draft');
            $table->timestamps();
        });
    }
    public function down(): void { Schema::dropIfExists('museum_visitor_contacts'); }
};
