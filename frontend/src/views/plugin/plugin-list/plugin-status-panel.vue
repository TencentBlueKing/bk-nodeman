<template>
  <ul class="task-list">
    <li class="task-item" v-for="item in tasks" :key="item.id">
      <span class="task-name">{{ item.name }}</span>
      <div class="task-status">
        <PluginStatusBox :status="item.status.toLocaleLowerCase()" />
      </div>
    </li>
  </ul>
</template>
<script lang="ts">
import { Vue, Component, Prop } from 'vue-property-decorator';
import { ITask } from '@/types/plugin/plugin-type';
import PluginStatusBox from './plugin-status-box.vue';

@Component({
  name: 'plugin-status-panel',
  components: {
    PluginStatusBox,
  },
})
export default class PluginStatusPanel extends Vue {
  @Prop({ default: () => [], type: Array }) private readonly tasks!: ITask[];
}
</script>
<style lang="postcss" scoped>
.task-list {
  padding: 3px 2px;
  font-size: 12px;
  overflow: auto;
}
.task-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.task-item + .task-item {
  margin-top: 10px;
}
.task-name {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
}
.task-status {
  margin-left: 20px;
  width: 60px;
}
.status-success {
  border-color: #e5f6ea;
  background: #3fc06d;
}
.status-failed {
  border-color: #ffe6e6;
  background: #ea3636;
}
</style>
