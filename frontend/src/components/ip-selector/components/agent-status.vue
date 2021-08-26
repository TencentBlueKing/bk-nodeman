<template>
  <ul class="agent-status">
    <li v-for="(item, index) in data" :key="index">
      <div v-if="type === 0">
        <span :class="['status-font', `status-${String(item.status).toLocaleLowerCase()}`]"
              v-show="item.display">
          {{ item.count }}
        </span>
        <span>{{ item.display | filterEmpty }}</span>
        <span class="separator" v-if="index !== (data.length - 1)">, </span>
      </div>
      <div v-else-if="type === 1">
        <span :class="['status-mark', `status-${String(item.status).toLocaleLowerCase()}`]">
        </span>
        <span>{{ item.display | filterEmpty }}</span>
      </div>
      <!-- 扩散点状态样式 -->
      <div class="agent-status-2" v-else-if="type === 2">
        <span :class="['status-halo', `status-${String(item.status).toLocaleLowerCase()}-halo`]">
        </span>
        <span>{{ item.display | filterEmpty }}</span>
      </div>
      <div v-else>
        <span :class="['status-count', !!item.errorCount ? 'status-terminated' : 'status-2']">
          {{ item.errorCount || 0 }}
        </span>
        <span>{{ item.count || 0 }}</span>
      </div>
    </li>
  </ul>
</template>
<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { IAgentStatusData } from '../types/selector-type';

@Component({ name: 'agent-status' })
export default class AgentStatus extends Vue {
  @Prop({ default: 0, type: Number }) private readonly type!: 0 | 1 | 2;
  @Prop({ default: () => [], type: Array }) private readonly data!: IAgentStatusData[];
}
</script>
<style lang="scss" scoped>

@mixin normal {
  border-color: #3fc06d;
  background: #86e7a9;
  color: #3fc06d;
}
@mixin error {
  border-color: #ea3636;
  background: #fd9c9c;
  color: #ea3636;
}
@mixin unknown {
  border-color: #c4c6cc;
  background: #f0f1f5;
  color: #c4c6cc;
}

.separator {
  padding: 0 2px;
}
.agent-status {
  display: flex;
  align-items: center;
  &-2 {
    display: flex;
    align-items: center;
  }
}
.status-mark {
  margin-right: 8px;
  width: 8px;
  height: 8px;
  border-radius: 4px;
  border: 1px solid;
  display: inline-block;
}
.status-font {
  font-weight: 700;

  /* stylelint-disable-next-line declaration-no-important */
  background: unset !important;
}
.status-halo {
  display: inline-block;
  margin-right: 8px;
  width: 13px;
  height: 13px;
  border: 3px solid;
  border-radius: 6.5px;
}
.status-count {
  /* stylelint-disable-next-line declaration-no-important */
  background: unset !important;
  &::after {
    content: "/";
    color: #63656e;
  }
}
.status-running,
.status-1 {
  @include normal;
}
.status-terminated,
.status-3 {
  @include error;
}
.status-unknown,
.status-2 {
  @include unknown;
}
.status-running-halo {
  border-color: #e5f6ea;
  background: #3fc06d;
}
.status-terminated-halo {
  border-color: #ffe6e6;
  background: #ea3636;
}
.status-unknown-halo {
  border-color: #f0f1f5;
  background: #b2b5bd;
}
</style>
