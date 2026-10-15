<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\Hash;
use MoonShine\Laravel\Models\MoonshineUser;
use MoonShine\Laravel\Models\MoonshineUserRole;

final class IsolatedBrowserQaSeeder extends Seeder
{
    public function run(): void
    {
        if (! app()->environment('testing') || ! getenv('MUSBREAD_E2E_PASSWORD')
            || ! getenv('MUSBREAD_E2E_USERNAME')) {
            throw new \RuntimeException('Isolated QA seeder requires testing env and ephemeral credentials');
        }

        MoonshineUser::query()->create([
            'moonshine_user_role_id' => MoonshineUserRole::DEFAULT_ROLE_ID,
            'name' => 'Automated QA (isolated)',
            'email' => getenv('MUSBREAD_E2E_USERNAME'),
            'password' => Hash::make(getenv('MUSBREAD_E2E_PASSWORD')),
        ]);
    }
}
