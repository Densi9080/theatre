<template>
  <q-layout view="lHh Lpr lFf" class="bg-grey-2">
    <!-- Хедер -->
    <q-header elevated class="bg-grey-9 text-white">
      <q-toolbar>
        <q-btn flat to="/">
          <img src="theatre_logo.jpg" height="105" />
        </q-btn>
        <q-btn flat label="Главная страница" to="/" />
        <q-btn flat label="Спектакли" to="/shows" />
        <q-btn flat label="Новости" to="/news" />
        <q-btn flat label="Мои билеты" to="/my-tickets" />
        <q-btn flat label="Регистрация" to="/registration" />
        <q-btn flat label="Войти" to="/login" />
        <q-btn flat label="Профиль" to="/profile" />
        <q-btn flat label="Выход" @click="onLogout()"/>
        <q-btn flat label="Админка" href="http://localhost:8000/admin/" target="_blank" />

        <q-btn-dropdown flat color="white" label="Прочее">
          <q-list style="min-width: 180px">
            <q-item clickable v-ripple to="/actors">
              <q-item-section>Актеры</q-item-section>
            </q-item>

            <q-item clickable v-ripple to="/genres">
              <q-item-section>Жанры</q-item-section>
            </q-item>
          </q-list>
        </q-btn-dropdown>

      </q-toolbar>
    </q-header>

    <!-- Основной контент -->
    <q-page-container>
      <router-view />
    </q-page-container>

    <!-- Футер -->
    <q-footer elevated class="bg-grey-9 text-white">
      <q-toolbar>
      </q-toolbar>
    </q-footer>
  </q-layout>
</template>

<script setup>
  import axios from 'axios';
  const onLogout=async()=>{
    await axios.post("/api/users/logout/")
  }
</script>

<style></style>
