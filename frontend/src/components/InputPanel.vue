<template>
  <div class="input-panel">
    <div class="input-wrapper">
      <el-input
        v-model="inputText"
        :disabled="disabled"
        :placeholder="placeholder"
        class="input-field"
        @keydown.enter.exact="handleSend"
        @keydown.shift.enter="inputText += '\n'"
        resize="none"
        :autosize="{ minRows: 1, maxRows: 4 }"
        type="textarea"
      >
        <template #suffix>
          <el-button
            type="primary"
            :icon="Promotion"
            circle
            size="small"
            :disabled="!inputText.trim() || disabled"
            @click="handleSend"
            class="send-btn"
          />
        </template>
      </el-input>
    </div>
    <p class="input-hint">按 Enter 发送，Shift + Enter 换行</p>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { Promotion } from '@element-plus/icons-vue'

const props = defineProps({
  disabled: {
    type: Boolean,
    default: false
  },
  placeholder: {
    type: String,
    default: '输入你的问题，例如：明天去武汉大学需要带伞吗？'
  },
  modelValue: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['send', 'update:modelValue'])
const inputText = ref(props.modelValue)

watch(inputText, (val) => emit('update:modelValue', val))
watch(() => props.modelValue, (val) => { inputText.value = val })

function handleSend() {
  const text = inputText.value.trim()
  if (!text || props.disabled) return
  emit('send', text)
  inputText.value = ''
}
</script>

<style scoped>
.input-panel {
  padding: 12px 20px 16px;
  border-top: 1px solid var(--border-color);
  background: #fff;
}

.input-wrapper {
  position: relative;
}

.input-field {
  --el-input-border-radius: var(--radius);
}

.input-field :deep(.el-textarea__inner) {
  padding: 10px 44px 10px 14px;
  line-height: 1.5;
  font-size: 14px;
  border-radius: var(--radius);
  border-color: var(--border-color);
  resize: none;
}

.input-field :deep(.el-textarea__inner):focus {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.send-btn {
  position: absolute;
  right: 6px;
  bottom: 6px;
  z-index: 10;
}

.input-hint {
  text-align: center;
  font-size: 11px;
  color: #c0c4cc;
  margin-top: 8px;
}
</style>
