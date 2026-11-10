/**
 * Image Cropper Modal - LIVRE DIA
 * Cropper.js integration para edição de imagens de perfil
 */

document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('dropzone-file');
    if (!fileInput) return; // Sai se não estiver na página de perfil

    let cropper = null;
    let currentFile = null;

    // Criar modal dinamicamente
    const modalHTML = `
        <div id="crop-modal" class="fixed inset-0 flex items-center justify-center bg-black/80 p-2" style="display: none; z-index: 99999; position: fixed; top: 0; left: 0; right: 0; bottom: 0; width: 100vw; height: 100vh; overflow: auto; -webkit-overflow-scrolling: touch; -webkit-transform: translateZ(0); transform: translateZ(0); will-change: transform;">
            <div class="relative w-full max-w-md sm:max-w-lg lg:max-w-2xl mx-2 sm:mx-4 bg-background-light dark:bg-background-dark rounded-lg shadow-2xl" style="max-height: 95vh; overflow-y: auto; -webkit-transform: translateZ(0); transform: translateZ(0);">
                <!-- Header -->
                <div class="flex items-center justify-between p-3 sm:p-4 border-b border-border-light dark:border-border-dark">
                    <h3 class="text-base sm:text-lg font-bold text-text-light dark:text-text-dark font-display">Ajustar Foto de Perfil</h3>
                    <button id="close-crop-modal" class="p-2 rounded-lg hover:bg-secondary-light dark:hover:bg-secondary-dark transition-colors">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5 text-text-light dark:text-text-dark">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                <!-- Área de Crop -->
                <div class="p-4 sm:p-6">
                    <div class="w-full bg-secondary-light dark:bg-secondary-dark rounded-lg overflow-hidden" style="height: 280px; max-height: 50vh;">
                        <img id="crop-image" src="" alt="Preview" class="max-w-full block">
                    </div>
                </div>

                <!-- Controles -->
                <div class="flex flex-col sm:flex-row items-center justify-between gap-3 p-3 sm:p-4 border-t border-border-light dark:border-border-dark bg-secondary-light/30 dark:bg-secondary-dark/30">
                    <div class="flex gap-2">
                        <button id="rotate-left" class="p-2 rounded-lg bg-background-light dark:bg-background-dark hover:bg-border-light dark:hover:bg-border-dark transition-colors" title="Girar à esquerda">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5 text-text-light dark:text-text-dark">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M9 15 3 9m0 0 6-6M3 9h12a6 6 0 0 1 0 12h-3" />
                            </svg>
                        </button>
                        <button id="rotate-right" class="p-2 rounded-lg bg-background-light dark:bg-background-dark hover:bg-border-light dark:hover:bg-border-dark transition-colors" title="Girar à direita">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5 text-text-light dark:text-text-dark">
                                <path stroke-linecap="round" stroke-linejoin="round" d="m15 15 6-6m0 0-6-6m6 6H9a6 6 0 0 0 0 12h3" />
                            </svg>
                        </button>
                        <button id="zoom-in" class="p-2 rounded-lg bg-background-light dark:bg-background-dark hover:bg-border-light dark:hover:bg-border-dark transition-colors" title="Ampliar">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5 text-text-light dark:text-text-dark">
                                <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607ZM10.5 7.5v6m3-3h-6" />
                            </svg>
                        </button>
                        <button id="zoom-out" class="p-2 rounded-lg bg-background-light dark:bg-background-dark hover:bg-border-light dark:hover:bg-border-dark transition-colors" title="Reduzir">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5 text-text-light dark:text-text-dark">
                                <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607ZM13.5 10.5h-6" />
                            </svg>
                        </button>
                    </div>
                    <div class="flex gap-2 w-full sm:w-auto">
                        <button id="cancel-crop" class="flex-1 sm:flex-none px-4 py-2 rounded-lg bg-background-light dark:bg-background-dark hover:bg-border-light dark:hover:bg-border-dark text-text-light dark:text-text-dark font-medium transition-colors">
                            Cancelar
                        </button>
                        <button id="confirm-crop" class="flex-1 sm:flex-none px-4 py-2 rounded-lg bg-primary hover:bg-primary/90 text-white font-bold transition-colors">
                            Confirmar
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Adicionar modal ao body
    document.body.insertAdjacentHTML('beforeend', modalHTML);

    // Elementos do modal
    const modal = document.getElementById('crop-modal');
    const cropImage = document.getElementById('crop-image');
    const closeModalBtn = document.getElementById('close-crop-modal');
    const cancelBtn = document.getElementById('cancel-crop');
    const confirmBtn = document.getElementById('confirm-crop');
    const rotateLeftBtn = document.getElementById('rotate-left');
    const rotateRightBtn = document.getElementById('rotate-right');
    const zoomInBtn = document.getElementById('zoom-in');
    const zoomOutBtn = document.getElementById('zoom-out');

    // Quando o usuário seleciona um arquivo
    fileInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (!file) return;

        // Validar tipo de arquivo
        if (!file.type.match(/^image\/(png|jpeg|jpg|gif)$/)) {
            alert('Por favor, selecione uma imagem válida (PNG, JPG ou GIF)');
            fileInput.value = '';
            return;
        }

        currentFile = file;

        // Criar URL temporária para preview
        const reader = new FileReader();
        reader.onload = function(event) {
            cropImage.src = event.target.result;

            // Prevenir scroll do body (importante para iOS)
            document.body.style.overflow = 'hidden';
            document.body.style.position = 'fixed';
            document.body.style.width = '100%';
            document.body.style.top = '0';

            // Mostrar modal - agora funciona corretamente sem conflito com Tailwind
            modal.style.display = 'flex';

            // Forçar reflow (importante para iOS)
            void modal.offsetHeight;

            // Pequeno timeout para garantir renderização no iOS
            setTimeout(() => {
                // Inicializar Cropper.js
                if (cropper) {
                    cropper.destroy();
                }

                cropper = new Cropper(cropImage, {
                    aspectRatio: 1, // Quadrado para foto de perfil
                    viewMode: 2,
                    dragMode: 'move',
                    autoCropArea: 1,
                    restore: false,
                    guides: true,
                    center: true,
                    highlight: false,
                    cropBoxMovable: true,
                    cropBoxResizable: true,
                    toggleDragModeOnDblclick: false,
                });
            }, 50);
        };

        reader.readAsDataURL(file);
    });

    // Botão de fechar modal
    closeModalBtn.addEventListener('click', closeModal);
    cancelBtn.addEventListener('click', closeModal);

    // Controles de rotação e zoom
    rotateLeftBtn.addEventListener('click', () => cropper && cropper.rotate(-90));
    rotateRightBtn.addEventListener('click', () => cropper && cropper.rotate(90));
    zoomInBtn.addEventListener('click', () => cropper && cropper.zoom(0.1));
    zoomOutBtn.addEventListener('click', () => cropper && cropper.zoom(-0.1));

    // Confirmar crop
    confirmBtn.addEventListener('click', function() {
        if (!cropper) return;

        // Obter canvas com imagem cropada
        const canvas = cropper.getCroppedCanvas({
            width: 400,
            height: 400,
            imageSmoothingQuality: 'high'
        });

        // Verificar se canvas foi gerado corretamente
        if (!canvas) {
            console.warn('Não foi possível gerar o canvas da imagem cropada');
            closeModal();
            return;
        }

        // Converter canvas para blob
        canvas.toBlob(function(blob) {
            // Criar novo File object
            const croppedFile = new File([blob], currentFile.name, {
                type: currentFile.type,
                lastModified: Date.now()
            });

            // Criar DataTransfer para atualizar o input
            const dataTransfer = new DataTransfer();
            dataTransfer.items.add(croppedFile);
            fileInput.files = dataTransfer.files;

            // Obter dataURL da imagem cropada
            const dataURL = canvas.toDataURL(currentFile.type, 0.95);

            // Atualizar preview
            updatePreview(dataURL);

            // Salvar base64 no campo hidden para persistir em caso de erro de validação
            // Busca por name (mais confiável que ID, pois Django pode adicionar prefixo "id_")
            const fotoBase64Input = document.querySelector('input[name="foto_base64"]');
            if (fotoBase64Input) {
                fotoBase64Input.value = dataURL;
            }

            // Fechar modal
            closeModal();
        }, currentFile.type, 0.95);
    });

    // Função para fechar modal
    function closeModal() {
        // Restaurar scroll do body
        document.body.style.overflow = '';
        document.body.style.position = '';
        document.body.style.width = '';
        document.body.style.top = '';

        modal.style.display = 'none';
        if (cropper) {
            cropper.destroy();
            cropper = null;
        }
    }

    // Função para atualizar preview (otimizada para mobile)
    function updatePreview(dataURL) {
        const currentPhotoDisplay = document.getElementById('current-photo-display');
        if (!currentPhotoDisplay) return;

        // Limpar conteúdo anterior completamente
        currentPhotoDisplay.innerHTML = '';

        // Criar nova imagem com tamanho fixo igual ao original (w-28 h-28 = 112px)
        const img = document.createElement('img');
        img.src = dataURL;
        img.alt = 'Preview da foto';
        img.className = 'w-28 h-28 rounded-full object-cover border-4 border-primary shadow-lg';

        // Adicionar ao container
        currentPhotoDisplay.appendChild(img);

        // Forçar reflow para garantir renderização em mobile
        void currentPhotoDisplay.offsetHeight;

        // Mostrar seção "remover foto" quando foto é carregada
        const removePhotoSection = document.getElementById('remove-photo-section');
        if (removePhotoSection) {
            removePhotoSection.style.display = 'flex';
        }
    }

    // Fechar modal ao clicar fora
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            closeModal();
        }
    });

    // Fechar modal com ESC
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && modal.style.display === 'flex') {
            closeModal();
        }
    });
});
